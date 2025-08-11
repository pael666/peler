#!/usr/bin/env python3
# Discord SelfBot - Modified for Groq API and Random Reply
# Original By Viloid ( github.com/vsec7 )
# Use At Your Own Risk
# --- Groq Version ---

import requests, random, sys, yaml, time
from groq import Groq

class Discord:
    def __init__(self, t):
        self.base = "https://discord.com/api/v9"
        self.auth = { 'authorization': t }
        
    def getMe(self):
        try:
            u = requests.get(self.base + "/users/@me", headers=self.auth).json()
            return u
        except requests.exceptions.RequestException as e:
            print(f"Error fetching user details: {e}")
            return None
        
    def getMessage(self, cid, l):
        try:
            u = requests.get(self.base + "/channels/" + str(cid) + "/messages?limit=" + str(l), headers=self.auth).json()
            return u
        except requests.exceptions.RequestException as e:
            print(f"Error fetching messages: {e}")
            return []
        
    def sendMessage(self, cid, txt):     
        try:
            u = requests.post(self.base + "/channels/" + str(cid) + "/messages", headers=self.auth, json={ 'content': txt }).json()
            return u
        except requests.exceptions.RequestException as e:
            print(f"Error sending message: {e}")
            return None

    def replyMessage(self, cid, mid, txt):     
        try:
            u = requests.post(self.base + "/channels/" + str(cid) + "/messages", headers=self.auth, json={ 'content': txt, 'message_reference': { 'message_id': str(mid) } }).json()
            return u
        except requests.exceptions.RequestException as e:
            print(f"Error replying to message: {e}")
            return None

    def deleteMessage(self, cid, mid):
        try:
            u = requests.delete(self.base + "/channels/" + str(cid) + "/messages/" + str(mid), headers=self.auth)
            return u
        except requests.exceptions.RequestException as e:
            print(f"Error deleting message: {e}")
            return None

# Fungsi baru untuk berinteraksi dengan Groq API
def generate_with_groq(api_key, text_prompt):
    try:
        client = Groq(api_key=api_key)
        
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You're a casual chatterbox on Discord. Your style is short, casual, and to the point. NEVER reveal that you're an AI, bot, or language model. If asked, deflect the question with a joking tone or say you're not. Keep your replies short, 2-5 words, don't use strange symbols, and avoid using uncommon words.If someone asks for your badge, say you have 35, if someone asks for your level, say your level is 20, if someone asks for your country, say you are from Indonesia."
                },
                {
                    "role": "user",
                    "content": text_prompt,
                }
            ],
            model="llama3-8b-8192", # Menggunakan Llama 3, salah satu model terbaik di Groq
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"[GROQ ERROR] {e}")
        return "error, gabisa mikir."

def main():
    with open('config.yaml') as cfg:
        conf = yaml.load(cfg, Loader=yaml.FullLoader)

    if not conf.get('BOT_TOKEN'):
        print("[!] Tolong masukkan Discord Token di config.yaml!")
        sys.exit()

    if not conf.get('CHANNEL_ID'):
        print("[!] Tolong masukkan Channel ID di config.yaml!")
        sys.exit()

    if conf.get('MODE') == 'groq' and not conf.get('GROQ_API_KEY'):
        print("[!] Mode adalah 'groq', tapi GROQ_API_KEY tidak ditemukan di config.yaml!")
        sys.exit()

    mode = conf.get('MODE', "quote")
    delay = conf.get('DELAY', 15)
    del_after = conf.get('DEL_AFTER', False)
    groq_key = conf.get('GROQ_API_KEY')
    
    while True:
        for token in conf['BOT_TOKEN']:
            try:
                # --- PERBAIKAN: Inisialisasi Bot dan getMe() hanya sekali per token ---
                Bot = Discord(token)
                me_info = Bot.getMe()
                if not me_info or 'username' not in me_info:
                    print(f"[Error] {token[:15]}... : TOKEN TIDAK VALID")
                    continue # Lanjut ke token berikutnya
                
                me = me_info['username'] + "#" + me_info['discriminator']
                me_id = me_info['id']
                print(f"---[ Berhasil Login Sebagai: {me} ]---")

                for chan in conf['CHANNEL_ID']:
                    # Logika untuk setiap channel dimulai di sini
                    if mode == "groq":
                        recent_messages = Bot.getMessage(chan, 15)
                        if not recent_messages:
                            continue

                        message_to_reply = None
                        potential_targets = []

                        for msg in recent_messages:
                            # Lewati pesan dari diri sendiri
                            if msg['author']['id'] == me_id:
                                continue

                            # Prioritas 1: Cari balasan langsung ke bot
                            if 'referenced_message' in msg and msg.get('referenced_message') is not None:
                                # --- PERBAIKAN & DEBUGGING ---
                                ref_msg = msg['referenced_message']
                                # Periksa apakah 'author' dan 'id' ada sebelum diakses
                                if 'author' in ref_msg and 'id' in ref_msg['author']:
                                    ref_author_id = ref_msg['author']['id']
                                    print(f"[{me}][DEBUG] Pesan ini adalah balasan. ID Penulis Asli: {ref_author_id}. ID Bot: {me_id}")
                                    
                                    if ref_author_id == me_id:
                                        print(f"[{me}][TARGET] Ditemukan balasan untuk bot dari '{msg['author']['username']}'.")
                                        message_to_reply = msg
                                        break # Jika sudah ketemu, langsung hentikan pencarian
                                else:
                                    print(f"[{me}][DEBUG] Pesan adalah balasan, tapi data penulis asli tidak lengkap.")
                                # --- AKHIR PERBAIKAN ---

                            # Tambahkan pesan valid sebagai kandidat untuk dibalas acak
                            potential_targets.append(msg)
                        
                        # Prioritas 2: Jika tidak ada balasan langsung, pilih target acak
                        if message_to_reply is None and potential_targets:
                            message_to_reply = random.choice(potential_targets)
                            print(f"[{me}][TARGET] Tidak ada balasan, menargetkan pesan acak dari '{message_to_reply['author']['username']}'.")

                        if message_to_reply:
                            prompt = message_to_reply['content']
                            print(f"[{me}][DEBUG] Mengirim prompt ke Groq: '{prompt}'")
                            api_response = generate_with_groq(groq_key, prompt)

                            if conf.get('REPLY', True):
                                send = Bot.replyMessage(chan, message_to_reply['id'], api_response)
                            else:
                                send = Bot.sendMessage(chan, api_response)

                            print(f"[{me}][{chan}][GROQ] {api_response}")

                            if del_after and send and send.get('id'):
                                time.sleep(1)
                                Bot.deleteMessage(chan, send['id'])
                                print(f"[{me}][DELETE] {send['id']}")
                        else:
                            print(f"[{me}][SKIP] Tidak ada pesan baru untuk dibalas di channel {chan}.")
            
            except Exception as e:
                print(f"[Error Loop Utama untuk token {token[:15]}...] {e}")
        
        print(f"-------[ Jeda selama {delay} detik ]-------")
        time.sleep(delay)

if __name__ == '__main__':
    try:
        main()
    except FileNotFoundError:
        print("[FATAL ERROR] File 'config.yaml' tidak ditemukan! Silakan buat file tersebut.")
    except Exception as err:
        print(f"{type(err).__name__} : {err}")
