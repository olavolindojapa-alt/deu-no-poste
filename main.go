package main

import (
	"context"
	"fmt"
	"os"
	"strings"
	"time"

	_ "modernc.org/sqlite"
	"go.mau.fi/whatsmeow"
	"go.mau.fi/whatsmeow/store/sqlstore"
	"go.mau.fi/whatsmeow/types"
	waLog "go.mau.fi/whatsmeow/util/log"
	waProto "go.mau.fi/whatsmeow/binary/proto"
	"google.golang.org/protobuf/proto"
)

func main() {
	dbLog := waLog.Stdout("Database", "ERROR", true)
	clientLog := waLog.Stdout("Client", "ERROR", true)

	dbPath := os.Getenv("SESSION_DB")
	if dbPath == "" {
		dbPath = "file:whatsapp_session.db?_pragma=foreign_keys(1)"
	}
	container, err := sqlstore.New(context.Background(), "sqlite", dbPath, dbLog)
	if err != nil {
		fmt.Printf("Failed to open database: %v\n", err)
		os.Exit(1)
	}

	deviceStore, err := container.GetFirstDevice(context.Background())
	if err != nil {
		fmt.Printf("Failed to get device store: %v\n", err)
		os.Exit(1)
	}
	if deviceStore == nil || deviceStore.ID == nil {
		fmt.Println("No valid session. Run login.go locally first to generate whatsapp_session.db")
		os.Exit(1)
	}

	client := whatsmeow.NewClient(deviceStore, clientLog)
	err = client.Connect()
	if err != nil {
		fmt.Printf("Failed to connect to WhatsApp: %v\n", err)
		os.Exit(1)
	}
	defer client.Disconnect()
	fmt.Println("Successfully connected to WhatsApp!")
	fmt.Println("Aguardando sincronizacao inicial...")
	time.Sleep(5 * time.Second)

	targetJIDsStr := os.Getenv("TARGET_JID")
	grupoNome := os.Getenv("GRUPO_NOME")

	var targetJID types.JID

	if grupoNome != "" {
		groups, err := client.GetJoinedGroups(context.Background())
		if err != nil {
			fmt.Printf("Failed to list groups: %v\n", err)
			os.Exit(1)
		}
		found := false
		for _, g := range groups {
			if strings.EqualFold(g.Name, grupoNome) {
				targetJID = g.JID
				found = true
				fmt.Printf("Grupo encontrado pelo nome: %s (%s)\n", g.Name, g.JID)
				break
			}
		}
		if !found {
			fmt.Printf("Group '%s' not found. Groups available:\n", grupoNome)
			for _, g := range groups {
				fmt.Printf("  - %s (%s)\n", g.Name, g.JID)
			}
			os.Exit(1)
		}
	} else if targetJIDsStr != "" {
		TARGET_JID := strings.TrimSpace(strings.Split(targetJIDsStr, ",")[0])
		parsed, err := types.ParseJID(TARGET_JID)
		if err != nil {
			fmt.Printf("Error parsing JID: %v\n", err)
			os.Exit(1)
		}
		targetJID = parsed
	} else {
		fmt.Println("Error: set GRUPO_NOME or TARGET_JID")
		os.Exit(1)
	}

	caption := os.Getenv("CAPTION")

	imageFile := os.Getenv("IMAGE_FILE")
	if imageFile != "" {
		sendImage(client, targetJID, imageFile, caption)
	}

	messageText := os.Getenv("MESSAGE_TEXT")
	if messageText != "" {
		msg := &waProto.Message{Conversation: proto.String(messageText)}
		resp, err := client.SendMessage(context.Background(), targetJID, msg)
		if err != nil {
			fmt.Printf("Failed to send text: %v\n", err)
			os.Exit(1)
		}
		fmt.Printf("Text sent! (ID: %s)\n", resp.ID)
	}

	time.Sleep(2 * time.Second)
}

func sendImage(client *whatsmeow.Client, targetJID types.JID, path string, caption string) {
	data, err := os.ReadFile(path)
	if err != nil {
		fmt.Printf("Error reading image: %v\n", err)
		os.Exit(1)
	}

	resp, err := client.Upload(context.Background(), data, whatsmeow.MediaImage)
	if err != nil {
		fmt.Printf("Failed to upload image: %v\n", err)
		os.Exit(1)
	}

	img := &waProto.ImageMessage{
		URL:                 proto.String(resp.URL),
		Mimetype:            proto.String("image/png"),
		Caption:             proto.String(caption),
		MediaKey:            resp.MediaKey,
		FileEncSHA256:       resp.FileEncSHA256,
		FileSHA256:          resp.FileSHA256,
		FileLength:          proto.Uint64(uint64(resp.FileLength)),
		Height:              proto.Uint32(0),
		Width:               proto.Uint32(0),
		DirectPath:          proto.String(resp.DirectPath),
	}

	_, err = client.SendMessage(context.Background(), targetJID, &waProto.Message{ImageMessage: img})
	if err != nil {
		fmt.Printf("Failed to send image: %v\n", err)
		os.Exit(1)
	}
	fmt.Println("Image sent successfully!")
}
