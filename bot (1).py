import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
import anthropic

# ── Config ──────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

# Historial de conversación por usuario
conversation_history = {}

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

logging.basicConfig(level=logging.INFO)

# ── Handlers ────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Claude API conectado. Mandame cualquier mensaje.\n"
        "Comandos:\n/reset — limpiar historial\n/model — ver modelo activo"
    )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conversation_history[user_id] = []
    await update.message.reply_text("Historial limpiado.")

async def model_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Modelo: claude-sonnet-4-20250514")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    # Inicializar historial si no existe
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    # Agregar mensaje del usuario
    conversation_history[user_id].append({
        "role": "user",
        "content": user_text
    })

    # Mantener máximo 20 mensajes (10 turnos) para no gastar tokens
    if len(conversation_history[user_id]) > 20:
        conversation_history[user_id] = conversation_history[user_id][-20:]

    await update.message.chat.send_action("typing")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=conversation_history[user_id]
        )

        assistant_reply = response.content[0].text

        # Guardar respuesta en historial
        conversation_history[user_id].append({
            "role": "assistant",
            "content": assistant_reply
        })

        # Telegram tiene límite de 4096 chars por mensaje
        if len(assistant_reply) > 4000:
            for i in range(0, len(assistant_reply), 4000):
                await update.message.reply_text(assistant_reply[i:i+4000])
        else:
            await update.message.reply_text(assistant_reply)

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# ── Main ────────────────────────────────────────────────
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("model", model_info))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot corriendo...")
    app.run_polling()
