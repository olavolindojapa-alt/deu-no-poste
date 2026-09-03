import sqlite3
import base64
import gzip
import os

DB_PATH = 'whatsapp_session.db'

def vacuum_database(db_path):
    print("🧹 Pruning database...")
    try:
        conn = sqlite3.connect(db_path, isolation_level=None)
        cursor = conn.cursor()
        
        # Keep only the tables needed for authentication.
        # ALL other tables are regenerable by whatsmeow and are dropped to
        # keep the compressed+base64 session small enough for GitHub Secrets
        # (each secret value must be <= 48KB).
        tables_to_clear = [
            'whatsmeow_message_secrets',
            'whatsmeow_privacy_tokens',
            'whatsmeow_lid_map',
            'whatsmeow_app_state_mutation_macs',
            'whatsmeow_app_state_version',
            'whatsmeow_contacts',
            'whatsmeow_chat_settings',
            'whatsmeow_sender_keys',
            'whatsmeow_event_buffer',
            'whatsmeow_retry_buffer',
            'contacts', 'messages', 'message_media', 'receipts',
            'chats', 'chat_settings', 'group_info', 'group_participants',
            'message_edits', 'status_messages', 'message_labels',
            'message_polls', 'message_poll_votes', 'message_reactions'
        ]
        
        # Also trim the pre_keys table down (keep only the newest 10).
        try:
            cursor.execute(
                "DELETE FROM whatsmeow_pre_keys WHERE id NOT IN "
                "(SELECT id FROM whatsmeow_pre_keys ORDER BY id DESC LIMIT 10);"
            )
        except sqlite3.OperationalError:
            pass

        for table in tables_to_clear:
            try:
                cursor.execute(f"DELETE FROM {table};")
            except sqlite3.OperationalError:
                pass # Table doesn't exist, ignore
                
        # Vacuum to reclaim space
        conn.execute("VACUUM;")
        conn.commit()
        conn.close()
        print("✅ Database pruned successfully.")
    except Exception as e:
        print(f"❌ Error pruning database: {e}")
        return False
    return True

def compress_and_split(db_path):
    print("📦 Compressing and splitting database...")
    
    with open(db_path, "rb") as f:
        data = f.read()
        
    compressed_data = gzip.compress(data, compresslevel=9)
    encoded_data = base64.b64encode(compressed_data).decode('utf-8')
    
    midpoint = len(encoded_data) // 2
    part1 = encoded_data[:midpoint]
    part2 = encoded_data[midpoint:]
    
    print(f"\n🔐 Part 1 Size: {len(part1)} bytes")
    print(f"🔐 Part 2 Size: {len(part2)} bytes\n")
    
    with open("WHATSAPP_SESSION_PART1.txt", "w") as f:
        f.write(part1)
        
    with open("WHATSAPP_SESSION_PART2.txt", "w") as f:
        f.write(part2)
        
    print("🎉 Done! Open WHATSAPP_SESSION_PART1.txt and WHATSAPP_SESSION_PART2.txt")
    print("Paste their contents into your GitHub Repository Secrets as:")
    print(" - WHATSAPP_SESSION_PART1")
    print(" - WHATSAPP_SESSION_PART2")

if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"❌ Could not find {DB_PATH}. Make sure you ran 'go run login.go' first!")
        exit(1)
        
    if vacuum_database(DB_PATH):
        compress_and_split(DB_PATH)
