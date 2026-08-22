package handler

import (
	"bytes"
	"crypto/subtle"
	"encoding/json"
	"fmt"
	"html"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
	"unicode/utf8"
)

type telegramRequest struct {
	ChatID                string `json:"chat_id"`
	Text                  string `json:"text"`
	DisableWebPagePreview bool   `json:"disable_web_page_preview"`
}

type telegramResponse struct {
	OK          bool   `json:"ok"`
	Description string `json:"description,omitempty"`
}

func Handler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("X-Content-Type-Options", "nosniff")

	if r.Method != http.MethodPost && r.Method != http.MethodGet {
		w.Header().Set("Allow", "GET, POST")
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	botToken := strings.TrimSpace(os.Getenv("TELEGRAM_BOT_TOKEN"))
	chatID := strings.TrimSpace(os.Getenv("TELEGRAM_CHAT_ID"))
	relayKey := os.Getenv("RELAY_KEY")

	if botToken == "" || chatID == "" || relayKey == "" {
		http.Error(w, "server is not configured", http.StatusInternalServerError)
		return
	}

	// Ограничиваем размер тела запроса: для тестового relay больше не нужно.
	r.Body = http.MaxBytesReader(w, r.Body, 16<<10)
	if err := r.ParseForm(); err != nil {
		http.Error(w, "invalid form", http.StatusBadRequest)
		return
	}

	providedKey := r.FormValue("key")
	if subtle.ConstantTimeCompare([]byte(providedKey), []byte(relayKey)) != 1 {
		http.Error(w, "forbidden", http.StatusForbidden)
		return
	}

	text := strings.TrimSpace(r.FormValue("text"))
	if text == "" {
		http.Error(w, "message is empty", http.StatusBadRequest)
		return
	}
	if !utf8.ValidString(text) || utf8.RuneCountInString(text) > 3500 {
		http.Error(w, "message is too long or invalid", http.StatusBadRequest)
		return
	}

	// Добавляем серверную отметку времени, чтобы повторные тесты было легко отличать.
	text = fmt.Sprintf("%s\n\nОтправлено: %s UTC", text, time.Now().UTC().Format("2006-01-02 15:04:05"))

	payload, err := json.Marshal(telegramRequest{
		ChatID:                chatID,
		Text:                  text,
		DisableWebPagePreview: true,
	})
	if err != nil {
		http.Error(w, "failed to build telegram request", http.StatusInternalServerError)
		return
	}

	url := "https://api.telegram.org/bot" + botToken + "/sendMessage"
	req, err := http.NewRequestWithContext(r.Context(), http.MethodPost, url, bytes.NewReader(payload))
	if err != nil {
		http.Error(w, "failed to create telegram request", http.StatusInternalServerError)
		return
	}
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: 8 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		http.Error(w, "telegram request failed", http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(io.LimitReader(resp.Body, 64<<10))
	if err != nil {
		http.Error(w, "failed to read telegram response", http.StatusBadGateway)
		return
	}

	var tg telegramResponse
	_ = json.Unmarshal(body, &tg)
	if resp.StatusCode < 200 || resp.StatusCode >= 300 || !tg.OK {
		msg := "Telegram rejected the message"
		if tg.Description != "" {
			msg += ": " + tg.Description
		}
		http.Error(w, msg, http.StatusBadGateway)
		return
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(http.StatusOK)
	_, _ = fmt.Fprintf(w, `<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<title>Отправлено</title>
<style>
body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0b0d10;color:#f5f7fa;font-family:system-ui,sans-serif;padding:24px}
main{max-width:640px;border:1px solid #262b33;border-radius:20px;padding:28px;background:#13161b;text-align:center}
h1{margin-top:0}.ok{font-size:54px;margin:0 0 12px}p{color:#aab2bd;line-height:1.5}a{display:inline-block;margin-top:10px;color:#f5f7fa}
</style>
</head>
<body><main><div class="ok">✅</div><h1>Сообщение отправлено</h1><p>Telegram Bot API принял сообщение для чата %s.</p><a href="/">Вернуться назад</a></main></body>
</html>`, html.EscapeString(chatID))
}
