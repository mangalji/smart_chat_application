(function () {
  const logEl = document.getElementById("chat-log");
  if (!logEl) return;

  const roomId = logEl.dataset.roomId;
  const userId = parseInt(logEl.dataset.userId, 10);
  const input = document.getElementById("chat-input");
  const sendBtn = document.getElementById("chat-send");
  const fileInput = document.getElementById("chat-file");
  const uploadBtn = document.getElementById("chat-upload");
  const aiSuggest = document.getElementById("ai-suggest");
  const aiLang = document.getElementById("ai-lang");
  const aiTone = document.getElementById("ai-tone");
  const aiOut = document.getElementById("ai-output");

  function getCookie(name) {
    const v = document.cookie.match("(^|;) ?" + name + "=([^;]*)(;|$)");
    return v ? decodeURIComponent(v[2]) : "";
  }

  const csrftoken =
    document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || getCookie("csrftoken");

  function scrollBottom() {
    logEl.scrollTop = logEl.scrollHeight;
  }
  scrollBottom();

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function appendBubble(payload) {
    const own = parseInt(payload.sender_id, 10) === userId;
    const wrap = document.createElement("div");
    wrap.className = "msg-bubble " + (own ? "msg-own" : "msg-other");
    wrap.dataset.msgId = String(payload.message_id);
    let html =
      '<div class="msg-meta">' +
      escapeHtml(payload.sender_name || payload.sender_email || "") +
      "</div>";
    if (payload.body) {
      html += '<div class="msg-text">' + escapeHtml(payload.body).replace(/\n/g, "<br>") + "</div>";
    }
    if (payload.has_media && payload.media_url) {
      const name = escapeHtml(payload.media_name || "Attachment");
      html += '<div class="mt-1"><a href="' + escapeHtml(payload.media_url) + '" target="_blank" rel="noopener">' + name + "</a>";
      const low = (payload.media_url || "").toLowerCase();
      if (/\.(png|jpe?g|gif|webp)(\?|$)/i.test(low)) {
        html +=
          '<div class="mt-2"><img src="' +
          escapeHtml(payload.media_url) +
          '" alt="" class="img-fluid rounded" style="max-height:220px;"></div>';
      }
      html += "</div>";
    }
    html += '<div class="msg-meta">' + escapeHtml(payload.created_at || "") + "</div>";
    wrap.innerHTML = html;
    logEl.appendChild(wrap);
    scrollBottom();
  }

  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(scheme + "://" + window.location.host + "/ws/chat/" + roomId + "/");

  ws.onmessage = function (ev) {
    try {
      const data = JSON.parse(ev.data);
      if (data.event === "message") {
        appendBubble(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  ws.onclose = function () {
    const bar = document.createElement("div");
    bar.className = "alert alert-warning small mt-2";
    bar.textContent = "Connection closed. Refresh the page to reconnect.";
    logEl.parentElement.appendChild(bar);
  };

  function sendText() {
    const body = (input.value || "").trim();
    if (!body || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: "chat_message", body: body }));
    input.value = "";
  }

  sendBtn.addEventListener("click", sendText);
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendText();
    }
  });

  uploadBtn.addEventListener("click", function () {
    const f = fileInput.files && fileInput.files[0];
    if (!f) {
      alert("Choose a file first.");
      return;
    }
    const fd = new FormData();
    fd.append("file", f);
    fd.append("csrfmiddlewaretoken", csrftoken);
    uploadBtn.disabled = true;
    fetch("/room/" + roomId + "/upload/", {
      method: "POST",
      body: fd,
      headers: { "X-CSRFToken": csrftoken },
      credentials: "same-origin",
    })
      .then(function (r) {
        return r.json().then(function (j) {
          if (!r.ok) throw new Error(j.error || "Upload failed");
          return j;
        });
      })
      .then(function () {
        fileInput.value = "";
      })
      .catch(function (err) {
        alert(err.message || String(err));
      })
      .finally(function () {
        uploadBtn.disabled = false;
      });
  });

  if (aiSuggest) {
    aiSuggest.addEventListener("click", function () {
      aiOut.classList.remove("d-none");
      aiOut.textContent = "Thinking…";
      fetch("/api/suggest-reply/", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrftoken,
        },
        body: JSON.stringify({
          room_id: parseInt(roomId, 10),
          language: aiLang ? aiLang.value : "en",
          tone: aiTone ? aiTone.value : "professional",
        }),
      })
        .then(function (r) {
          return r.json().then(function (j) {
            if (!r.ok) throw new Error(j.error || "Request failed");
            return j;
          });
        })
        .then(function (j) {
          aiOut.textContent = j.suggestion || "";
          if (input && j.suggestion) {
            input.value = j.suggestion;
            input.focus();
          }
        })
        .catch(function (err) {
          aiOut.textContent = err.message || String(err);
        });
    });
  }
})();
