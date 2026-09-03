package main

import (
	"context"
	"flag"
	"fmt"
	"image"
	"image/color"
	"image/png"
	"os"
	"os/signal"
	"syscall"
	"time"

	_ "modernc.org/sqlite"
	"go.mau.fi/whatsmeow"
	"go.mau.fi/whatsmeow/store/sqlstore"
	waLog "go.mau.fi/whatsmeow/util/log"
	"rsc.io/qr"
)

func savePNG(code *qr.Code, modulePx int) {
	n := code.Size
	// quiet zone: 4 empty modules on each side (required for scanners)
	quiet := 4
	total := (n + 2*quiet) * modulePx
	img := image.NewGray(image.Rect(0, 0, total, total))
	white := color.Gray{255}
	black := color.Gray{0}
	for y := 0; y < total; y++ {
		for x := 0; x < total; x++ {
			// module coordinates (removing quiet zone)
			my := (y / modulePx) - quiet
			mx := (x / modulePx) - quiet
			c := white
			if mx >= 0 && mx < n && my >= 0 && my < n && code.Black(mx, my) {
				c = black
			}
			img.Set(x, y, c)
		}
	}
	f, err := os.Create("qr_login.png")
	if err != nil {
		fmt.Println("erro criando qr_login.png:", err)
		return
	}
	defer f.Close()
	png.Encode(f, img)
}

func main() {
	phone := flag.String("phone", "", "numero de telefone com DDI e DDD (ex: -phone 5511999999999). Gera codigo de 8 digitos em vez de QR.")
	flag.Parse()

	dbLog := waLog.Stdout("Database", "ERROR", true)
	dbPath := os.Getenv("SESSION_DB")
	if dbPath == "" {
		dbPath = "file:whatsapp_session.db?_pragma=foreign_keys(1)"
	}
	container, err := sqlstore.New(context.Background(), "sqlite", dbPath, dbLog)
	if err != nil {
		panic(err)
	}

	deviceStore, err := container.GetFirstDevice(context.Background())
	if err != nil {
		panic(err)
	}

	clientLog := waLog.Stdout("Client", "ERROR", true)
	client := whatsmeow.NewClient(deviceStore, clientLog)

	if client.Store.ID == nil {
		fmt.Println("ATENCAO: feche outras janelas de login. So UM processo deve rodar.")
		if *phone == "" {
			fmt.Println("Modo QR: sera salvo em qr_login.png (imagem, 800px).")
			fmt.Println("Abra a imagem e escaneie com: WhatsApp > Aparelhos conectados")
		} else {
			fmt.Println("Modo numero de telefone: sera gerado um codigo de 8 digitos.")
			fmt.Println("No celular: Configuracoes > Aparelhos conectados > Conectar um aparelho > Conectar com numero de telefone.")
		}
		qrChan, _ := client.GetQRChannel(context.Background())
		err = client.Connect()
		if err != nil {
			panic(err)
		}

		if *phone != "" {
			// wait for the first QR/channel event so the websocket is established,
			// then request the 8-digit pairing code (ignore the QR itself)
			<-qrChan
			code, err := client.PairPhone(context.Background(), *phone, true, whatsmeow.PairClientChrome, "Chrome (Windows)")
			if err != nil {
				fmt.Println("Erro no PairPhone:", err)
				fmt.Println("Dica: use o numero com DDI+DDD, ex: -phone 5511999999999")
				client.Disconnect()
				return
			}
			fmt.Println()
			fmt.Println("==============================================")
			fmt.Println("  CODIGO DE 8 DIGITOS PARA DIGITAR NO CELULAR:")
			fmt.Println("  " + code)
			fmt.Println("==============================================")
			fmt.Println("No celular: Aparelhos conectados > Conectar com numero de telefone, digite este codigo.")
			fmt.Println("Aguardando confirmacao... (ate 160s)")
		}

		// drain the channel until pairing completes (success) or errors
		for evt := range qrChan {
			if *phone == "" && evt.Event == "code" {
				if code, err := qr.Encode(evt.Code, qr.M); err == nil {
					modulePx := 800 / (code.Size + 8)
					if modulePx < 8 {
						modulePx = 8
					}
					savePNG(code, modulePx)
					fmt.Println("QR salvo em qr_login.png - escaneie com o celular")
				}
				continue
			}
			if evt.Event == "success" {
				break
			}
			if evt.Event == "error" {
				fmt.Println("Erro no pareamento:", evt.Error)
				client.Disconnect()
				return
			}
		}

		// keep the process alive so whatsmeow persists the device ID
		fmt.Println("Pareado! Aguardando a sessao ser salva no banco...")
		time.Sleep(8 * time.Second)
		fmt.Println("Sessao salva. Abra o whatsapp_session.db.")
		client.Disconnect()
		os.Exit(0)
	} else {
		err = client.Connect()
		if err != nil {
			panic(err)
		}
		fmt.Println("Already logged in! You don't need to scan again.")
		c := make(chan os.Signal, 1)
		signal.Notify(c, os.Interrupt, syscall.SIGTERM)
		<-c
		client.Disconnect()
	}
}
