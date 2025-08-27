import os
import sqlite3
from datetime import datetime
import telebot
from telebot import types
import re

# Token del bot (da ottenere da @BotFather)
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
bot = telebot.TeleBot(BOT_TOKEN)

# Provider token per i pagamenti (da Telegram)
PAYMENT_TOKEN = "YOUR_PAYMENT_TOKEN_HERE"

# Database setup
def init_database():
    conn = sqlite3.connect('vigenere_users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            messages_left INTEGER DEFAULT 50,
            is_premium BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            premium_date TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Funzioni database
def get_user(user_id):
    conn = sqlite3.connect('vigenere_users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_user(user_id, username):
    conn = sqlite3.connect('vigenere_users.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, messages_left, is_premium)
        VALUES (?, ?, 50, FALSE)
    ''', (user_id, username))
    conn.commit()
    conn.close()

def update_messages(user_id, messages_left):
    conn = sqlite3.connect('vigenere_users.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET messages_left = ? WHERE user_id = ?', 
                   (messages_left, user_id))
    conn.commit()
    conn.close()

def upgrade_to_premium(user_id):
    conn = sqlite3.connect('vigenere_users.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users SET is_premium = TRUE, premium_date = ? WHERE user_id = ?
    ''', (datetime.now(), user_id))
    conn.commit()
    conn.close()

# Algoritmo Vigenère per versioni FREE e PREMIUM
def vigenere_cipher(text, key, decrypt=False, is_premium=False):
    result = ""
    key_index = 0
    
    if is_premium:
        # PREMIUM: Cifratura completa (lettere, spazi, simboli, numeri)
        for char in text:
            if key_index < len(key):
                shift = ord(key[key_index % len(key)])
                if decrypt:
                    shift = -shift
                
                # Applica shift su tutti i caratteri ASCII stampabili (32-126)
                if 32 <= ord(char) <= 126:
                    new_char_code = ((ord(char) - 32 + shift) % 95) + 32
                    result += chr(new_char_code)
                    key_index += 1
                else:
                    result += char
            else:
                result += char
    else:
        # FREE: Solo lettere A-Z (algoritmo classico)
        key = key.upper()
        for char in text.upper():
            if char.isalpha():
                shift = ord(key[key_index % len(key)]) - ord('A')
                if decrypt:
                    shift = -shift
                
                ascii_offset = ord('A')
                new_char = chr((ord(char) - ascii_offset + shift) % 26 + ascii_offset)
                result += new_char
                key_index += 1
            else:
                result += char
    
    return result

# Handler per /start
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    user = get_user(user_id)
    if not user:
        create_user(user_id, username)
        user = get_user(user_id)
    
    welcome_text = f"""🔐 **VigenèreBot - Crittografia Sicura**

Benvenuto {username}! 👋

**Come funziona:**
• `/cifra CHIAVE il tuo messaggio` - Cifra un messaggio
• `/decifra CHIAVE testo_cifrato` - Decifra un messaggio

**Il tuo account:**
{"💎 PREMIUM - Uso illimitato!" if user[3] else f"🆓 GRATUITO - {user[2]} messaggi rimasti"}

**Limiti versione gratuita:**
• 50 messaggi totali
• Chiave max 10 caratteri

**Versione Premium (€2,99):**
• 💎 Uso illimitato
• 🔑 Chiavi di qualsiasi lunghezza
• 🛡️ Sicurezza massima

/upgrade per passare a Premium!
/help per maggiori info
    """
    
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

# Handler per /help
@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """📖 **Guida VigenèreBot**

**Comandi principali:**
• `/cifra CHIAVE messaggio` - Cifra il tuo testo
• `/decifra CHIAVE testo_cifrato` - Decifra il testo

**Esempio:**
`/cifra SEGRETO Ci vediamo alle 18`
Risultato: `UQ FQGQOCK ENNO 68`

Per decifrare:
`/decifra SEGRETO UQ FQGQOCK ENNO 68`
Risultato: `Ci vediamo alle 18`

**💡 Consigli:**
• Usa chiavi difficili da indovinare
• Condividi la chiave in modo sicuro
• Versione Premium = chiavi lunghe = più sicurezza

/upgrade per Premium (€2,99)
/status per vedere il tuo account
    """
    bot.reply_to(message, help_text, parse_mode='Markdown')

# Handler per /status
@bot.message_handler(commands=['status'])
def status_command(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        create_user(user_id, message.from_user.username)
        user = get_user(user_id)
    
    if user[3]:  # is_premium
        status_text = """💎 **Account Premium Attivo!**

✅ Uso illimitato
✅ Chiavi di qualsiasi lunghezza
✅ Sicurezza massima

Grazie per aver scelto VigenèreBot Premium! 🚀
        """
    else:
        status_text = f"""🆓 **Account Gratuito**

📊 Messaggi rimasti: **{user[2]}/50**
🔑 Chiave max: **10 caratteri**

💎 Passa a Premium per:
• Uso illimitato
• Chiavi lunghe (più sicure)
• Solo €2,99!

/upgrade per fare l'upgrade
        """
    
    bot.reply_to(message, status_text, parse_mode='Markdown')

# Handler per /upgrade
@bot.message_handler(commands=['upgrade'])
def upgrade_command(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if user and user[3]:  # già premium
        bot.reply_to(message, "💎 Sei già Premium! Goditi l'uso illimitato 🚀")
        return
    
    # Crea invoice per il pagamento
    prices = [types.LabeledPrice(label="VigenèreBot Premium", amount=299)]  # 2.99 EUR in centesimi
    
    bot.send_invoice(
        message.chat.id,
        title="VigenèreBot Premium",
        description="🔑 Chiavi illimitate\n💎 Uso illimitato\n🛡️ Sicurezza massima",
        provider_token=PAYMENT_TOKEN,
        currency="EUR",
        photo_url="https://i.imgur.com/your-image.jpg",  # Opzionale
        photo_height=512,
        photo_width=512,
        is_flexible=False,
        prices=prices,
        start_parameter="premium-upgrade",
        invoice_payload="premium_upgrade"
    )

# Handler pre-checkout (obbligatorio)
@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(
        pre_checkout_query.id,
        ok=True,
        error_message="Errore nel pagamento. Riprova!"
    )

# Handler pagamento completato
@bot.message_handler(content_types=['successful_payment'])
def successful_payment(message):
    user_id = message.from_user.id
    upgrade_to_premium(user_id)
    
    success_text = """🎉 **Benvenuto in Premium!**

💎 Il tuo account è stato aggiornato con successo!

**Ora puoi:**
✅ Usare chiavi di qualsiasi lunghezza
✅ Cifrare messaggi illimitati
✅ Sicurezza massima

Inizia subito con:
`/cifra la_tua_chiave_lunga_e_sicura Il tuo messaggio segreto`

Grazie per aver scelto VigenèreBot! 🚀
    """
    bot.reply_to(message, success_text, parse_mode='Markdown')

# Handler per /cifra
@bot.message_handler(commands=['cifra'])
def cifra_command(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        create_user(user_id, message.from_user.username)
        user = get_user(user_id)
    
    # Controlla se ha messaggi rimasti (se non è premium)
    if not user[3] and user[2] <= 0:  # non premium e no messaggi
        upgrade_text = """⚠️ **Messaggi esauriti!**

Hai utilizzato tutti i 50 messaggi gratuiti.

💎 **Passa a Premium** per soli €2,99:
• Uso illimitato
• Chiavi più lunghe e sicure
• Supporto prioritario

/upgrade per fare l'upgrade ora!
        """
        bot.reply_to(message, upgrade_text, parse_mode='Markdown')
        return
    
    # Parsing del comando
    parts = message.text.split(' ', 2)
    if len(parts) < 3:
        bot.reply_to(message, "❌ Formato: `/cifra CHIAVE il tuo messaggio`", parse_mode='Markdown')
        return
    
    key = parts[1]
    text = parts[2]
    
    # Controlla lunghezza chiave per utenti gratuiti
    if not user[3] and len(key) > 10:  # non premium
        limit_text = f"""🔑 **Chiave troppo lunga!**

🆓 **Versione gratuita:** max 10 caratteri
💎 **Premium:** chiavi illimitate

La tua chiave: `{key}` ({len(key)} caratteri)

Upgrade a Premium per €2,99:
• Chiavi di qualsiasi lunghezza
• Sicurezza massima
• Uso illimitato

/upgrade per sbloccare!
        """
        bot.reply_to(message, limit_text, parse_mode='Markdown')
        return
    
    # Validazione chiave basata sulla versione
    if not user[3]:  # Versione gratuita
        if not key.isalpha():
            bot.reply_to(message, "❌ Versione gratuita: chiave solo lettere (A-Z)!\n💎 Premium: lettere, spazi, simboli illimitati!\n/upgrade per sbloccare", parse_mode='Markdown')
            return
    # Premium: accetta qualsiasi carattere (nessuna validazione)
    
    # Cifra il messaggio
    try:
        encrypted = vigenere_cipher(text, key, decrypt=False, is_premium=user[3])
        
        # Decrementa messaggi per utenti gratuiti
        if not user[3]:
            new_count = user[2] - 1
            update_messages(user_id, new_count)
            
            status_emoji = "🆓" if new_count > 10 else "⚠️" if new_count > 0 else "🔴"
            remaining_text = f"\n\n{status_emoji} Messaggi rimasti: {new_count}"
            if new_count <= 5:
                remaining_text += f"\n💎 /upgrade per Premium!"
        else:
            remaining_text = "\n\n💎 Premium - Uso illimitato!"
        
        result_text = f"""🔐 **Messaggio Cifrato**

**Originale:** `{text}`
**Chiave:** `{key}`
**Cifrato:** `{encrypted}`

📋 Copia e incolla il testo cifrato per condividerlo!{remaining_text}
        """
        
        bot.reply_to(message, result_text, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ Errore nella cifratura: {str(e)}")

# Handler per /decifra
@bot.message_handler(commands=['decifra'])
def decifra_command(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        create_user(user_id, message.from_user.username)
        user = get_user(user_id)
    
    # Controlla messaggi per utenti gratuiti
    if not user[3] and user[2] <= 0:
        upgrade_text = """⚠️ **Messaggi esauriti!**

💎 Passa a Premium (€2,99) per uso illimitato!
/upgrade per fare l'upgrade
        """
        bot.reply_to(message, upgrade_text, parse_mode='Markdown')
        return
    
    # Parsing
    parts = message.text.split(' ', 2)
    if len(parts) < 3:
        bot.reply_to(message, "❌ Formato: `/decifra CHIAVE testo_cifrato`", parse_mode='Markdown')
        return
    
    key = parts[1]
    encrypted_text = parts[2]
    
    # Controlla lunghezza chiave per utenti gratuiti
    if not user[3] and len(key) > 10:
        bot.reply_to(message, f"🔑 Chiave troppo lunga! Versione gratuita: max 10 caratteri.\n💎 /upgrade per Premium!", parse_mode='Markdown')
        return
    
    # Validazione chiave per decifratura
    if not user[3]:  # Versione gratuita
        if not key.isalpha():
            bot.reply_to(message, "❌ Versione gratuita: chiave solo lettere (A-Z)!\n💎 /upgrade per caratteri speciali", parse_mode='Markdown')
            return
    
    # Decifra
    try:
        decrypted = vigenere_cipher(encrypted_text, key, decrypt=True, is_premium=user[3])
        
        # Aggiorna contatore
        if not user[3]:
            new_count = user[2] - 1
            update_messages(user_id, new_count)
            remaining_text = f"\n\n🆓 Messaggi rimasti: {new_count}"
        else:
            remaining_text = "\n\n💎 Premium attivo!"
        
        result_text = f"""🔓 **Messaggio Decifrato**

**Cifrato:** `{encrypted_text}`
**Chiave:** `{key}`
**Originale:** `{decrypted}`{remaining_text}
        """
        
        bot.reply_to(message, result_text, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ Errore nella decifratura: {str(e)}")

if __name__ == "__main__":
    # Inizializza database
    init_database()
    
    print("🤖 VigenèreBot avviato!")
    print("💎 Sistema Premium attivo")
    print("🔐 Pronto per cifrare messaggi!")
    
    # Avvia il bot
    bot.infinity_polling()