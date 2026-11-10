import os
import time
import json
import base64
import hmac
import hashlib
import random
import requests
import telebot

# Yahan apna Telegram Bot Token daalein
TOKEN = "9052623880:AAH70-D-cGT1L9sl-3LJL206s4Qm5J0c0C0"
bot = telebot.TeleBot(TOKEN)

user_states = {}

def encrypt_payload(user_key, data_key, payload_obj):
    timestamp = int(time.time() * 1000)
    payload_obj["userKey"] = user_key
    payload_obj["t"] = timestamp

    json_str = json.dumps(payload_obj, separators=(',', ':'))
    a = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
    u = base64.b64encode(str(timestamp).encode('utf-8')).decode('utf-8')

    key = data_key[4:18]
    message = f"{u}.{a}"

    hmac_hex = hmac.new(key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()
    f = base64.b64encode(hmac_hex.encode('utf-8')).decode('utf-8')

    p = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    m = random.randint(1, 6)
    k = random.randint(2, 8)
    noise = "".join(random.choice(p) for _ in range(k))

    s = f"{k}{m}{f[:m]}{noise}{f[m:]}"
    g = f"{u}.{a}.{s}"

    return {
        "userKey": str(user_key),
        "data": g
    }

def decode_resp(text):
    try:
        j = json.loads(text)
        if "resp" in j:
            return json.loads(base64.b64decode(j["resp"]).decode('utf-8'))
        return j
    except Exception:
        return {"raw": text}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "🤖 **ITC Telegram Automation Bot**\n\nApna **10-digit mobile number** bhejein OTP request ke liye:", parse_mode="Markdown")
    user_states[message.chat.id] = {"step": "WAITING_MOBILE"}

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()
    state_data = user_states.get(chat_id, {})
    current_step = state_data.get("step")

    if current_step == "WAITING_MOBILE":
        if len(text) == 10 and text.isdigit():
            msg = bot.send_message(chat_id, f"⏳ Number `+91 {text}` ke liye OTP request ki ja rahi hai...", parse_mode="Markdown")
            
            names = ["Rahul Sharma", "Priya Patel", "Amit Verma", "Vikram Singh", "Pooja Das"]
            pins = ["110001", "380001", "226001", "500001", "400001"]
            
            try:
                sess = requests.Session()
                sess.headers.update({
                    "User-Agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
                    "Origin": "https://discoverworldblends.in",
                    "Referer": "https://discoverworldblends.in/",
                    "Content-Type": "application/json"
                })

                reg_payload = {
                    "name": random.choice(names),
                    "mobile": text,
                    "pincode": random.choice(pins),
                    "t": int(time.time() * 1000)
                }
                
                r = sess.post("https://discoverworldblends.in/api/users/register/", json=reg_payload, timeout=15)
                res_data = decode_resp(r.text)

                if res_data.get("statusCode") == 200 or "userKey" in res_data:
                    user_states[chat_id] = {
                        "step": "WAITING_OTP",
                        "userKey": res_data.get("userKey"),
                        "dataKey": res_data.get("dataKey"),
                        "mobile": text
                    }
                    bot.edit_message_text(
                        f"✅ **OTP Sent Successfully!**\n📱 Mobile: `{text}`\n\nAb apna **4-character OTP** yahan bhejein:",
                        chat_id=chat_id,
                        message_id=msg.message_id,
                        parse_mode="Markdown"
                    )
                else:
                    bot.edit_message_text(f"❌ Server Response: {res_data.get('message', 'Failed to send OTP')}", chat_id=chat_id, message_id=msg.message_id)
                    user_states.pop(chat_id, None)

            except Exception as e:
                bot.edit_message_text(f"❌ Error: {str(e)}", chat_id=chat_id, message_id=msg.message_id)
                user_states.pop(chat_id, None)
        else:
            bot.reply_to(message, "⚠️ Kripya valid 10-digit mobile number enter karein.")

    elif current_step == "WAITING_OTP":
        otp = text.upper()
        user_key = state_data.get("userKey")
        data_key = state_data.get("dataKey")
        
        msg = bot.send_message(chat_id, f"⚡ OTP `{otp}` verify ho raha hai...", parse_mode="Markdown")

        try:
            sess = requests.Session()
            sess.headers.update({
                "User-Agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
                "Origin": "https://discoverworldblends.in",
                "Referer": "https://discoverworldblends.in/",
                "Content-Type": "application/json"
            })

            # 1. Verify OTP
            verify_payload = encrypt_payload(user_key, data_key, {"otp": otp})
            r_ver = sess.post(f"https://discoverworldblends.in/api/users/verifyOTP/{user_key}", json=verify_payload, timeout=15)
            ver_res = decode_resp(r_ver.text)

            access_token = ver_res.get("accessToken")
            if not access_token:
                bot.edit_message_text(f"❌ OTP Failed: {ver_res.get('message', 'Invalid OTP')}", chat_id=chat_id, message_id=msg.message_id)
                return

            sess.headers.update({"Authorization": f"Bearer {access_token}"})

            # 2. Select Country & Answer Quiz
            sc_enc = encrypt_payload(user_key, data_key, {"country": "brazil"})
            sess.post(f"https://discoverworldblends.in/api/users/selectCountry/{user_key}", json=sc_enc, timeout=15)

            ans_enc = encrypt_payload(user_key, data_key, {"answer": "Rich, smooth and aromatic authentic coffee blend with distinct notes"})
            sess.post(f"https://discoverworldblends.in/api/users/answer/{user_key}", json=ans_enc, timeout=15)

            # 3. Spin Reward
            spin_enc = encrypt_payload(user_key, data_key, {"token": "direct_token"})
            spin_res_obj = sess.post(f"https://discoverworldblends.in/api/users/getReward/{user_key}", json=spin_enc, timeout=15)
            spin_data = decode_resp(spin_res_obj.text)

            reward_type = spin_data.get("rewardType", "Completed")

            result_text = (
                f"🎉 **Process Completed!** 🎉\n\n"
                f"🎁 **Reward:** `{reward_type}`\n"
                f"📄 **Details:**\n```json\n{json.dumps(spin_data, indent=2)}\n```\n\n"
                f"Naya number try karne ke liye `/start` bhejein."
            )
            bot.edit_message_text(result_text, chat_id=chat_id, message_id=msg.message_id, parse_mode="Markdown")

        except Exception as e:
            bot.edit_message_text(f"❌ Error: {str(e)}", chat_id=chat_id, message_id=msg.message_id)

        user_states.pop(chat_id, None)

    else:
        bot.reply_to(message, "Naya process shuru karne ke liye `/start` command bhejein.")

if __name__ == "__main__":
    print("[BOT] Bot is running...")
    bot.infinity_polling()
