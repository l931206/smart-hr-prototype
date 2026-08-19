(function () {
  const state = { user: null, leaveTypes: [], draftId: null, recognition: null };

  function pad(value) { return String(value).padStart(2, "0"); }
  function isoDate(date) { return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`; }
  function validDate(year, month, day) {
    const date = new Date(year, month - 1, day);
    return date.getFullYear() === year && date.getMonth() === month - 1 && date.getDate() === day ? date : null;
  }

  function resolveYearlessDate(month, day, today) {
    let date = validDate(today.getFullYear(), month, day);
    if (date && date < new Date(today.getFullYear(), today.getMonth(), today.getDate())) {
      date = validDate(today.getFullYear() + 1, month, day);
    }
    return date;
  }

  function extractDates(text, today = new Date()) {
    const dates = [];
    const absolutePattern = /(?:(\d{4})\s*[年\-/\.]\s*)?(\d{1,2})\s*[月\-/\.]\s*(\d{1,2})\s*日?/g;
    let match;
    while ((match = absolutePattern.exec(text)) && dates.length < 2) {
      const date = match[1]
        ? validDate(Number(match[1]), Number(match[2]), Number(match[3]))
        : resolveYearlessDate(Number(match[2]), Number(match[3]), today);
      if (date) dates.push(isoDate(date));
    }
    if (!dates.length) {
      const relativeDays = text.includes("後天") ? 2 : text.includes("明天") ? 1 : text.includes("今天") ? 0 : null;
      if (relativeDays !== null) {
        const date = new Date(today.getFullYear(), today.getMonth(), today.getDate() + relativeDays);
        dates.push(isoDate(date));
      }
    }
    return dates;
  }

  function extractReason(text) {
    const explicit = text.match(/(?:原因(?:是|為|[:：])?|因為|由於)\s*(.+)$/);
    if (explicit?.[1]) return explicit[1].trim().replace(/[。！!]$/, "");
    const clauses = text.split(/[，,。]/).map((value) => value.trim()).filter(Boolean);
    const candidate = clauses.find((value) => !/(請假|特休|事假|病假|公假|補休|婚假|喪假|月\d+日|\d{4}[-/]\d+)/.test(value));
    return candidate || "";
  }

  function parseLeaveMessage(text, leaveTypes, today = new Date()) {
    const cleanText = text.trim();
    const aliases = { "特休": "特休假", "年假": "特休假", "私人假": "事假" };
    let leaveType = leaveTypes.find((item) => cleanText.includes(item.name))?.name || "";
    if (!leaveType) {
      const alias = Object.keys(aliases).find((name) => cleanText.includes(name));
      const mapped = alias ? aliases[alias] : "";
      leaveType = leaveTypes.find((item) => item.name === mapped)?.name || "";
    }
    const dates = extractDates(cleanText, today);
    const afternoonOnly = cleanText.includes("下午") && !cleanText.includes("上午");
    const morningOnly = cleanText.includes("上午") && !cleanText.includes("下午");
    return {
      payload: {
        leave_type: leaveType,
        start_date: dates[0] || "",
        end_date: dates[1] || dates[0] || "",
        start_time: afternoonOnly ? "下午" : "上午",
        end_time: morningOnly ? "上午" : "下午",
        reason: extractReason(cleanText),
      },
      missing: [
        !leaveType && "假別",
        !dates.length && "日期",
        !extractReason(cleanText) && "原因",
      ].filter(Boolean),
    };
  }

  function appendMessage(kind, content, options = {}) {
    const messages = document.querySelector("#chatMessages");
    const row = document.createElement("div");
    row.className = `message ${kind}`;
    if (kind !== "user") {
      const avatar = document.createElement("span");
      avatar.className = "message-avatar";
      avatar.textContent = "HR";
      row.appendChild(avatar);
    }
    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    if (options.html) bubble.innerHTML = content;
    else {
      const paragraph = document.createElement("p");
      paragraph.textContent = content;
      bubble.appendChild(paragraph);
    }
    row.appendChild(bubble);
    messages.appendChild(row);
    messages.scrollTop = messages.scrollHeight;
    return bubble;
  }

  function addSuggestions(bubble) {
    const choices = ["我要請明天特休，原因是處理私人事務", "我要請 9 月 3 日公假，原因是參加教育訓練"];
    const wrap = document.createElement("div");
    wrap.className = "suggestions";
    choices.forEach((text) => {
      const button = document.createElement("button");
      button.className = "suggestion";
      button.type = "button";
      button.textContent = text;
      button.addEventListener("click", () => {
        document.querySelector("#assistantInput").value = text;
        document.querySelector("#assistantInput").focus();
      });
      wrap.appendChild(button);
    });
    bubble.appendChild(wrap);
  }

  function summaryHtml(summary) {
    const rows = [
      ["申請人", summary.employee_name], ["部門", summary.department || "—"],
      ["假別", summary.leave_type], ["日期", `${summary.start_date} 至 ${summary.end_date}`],
      ["時段", `${summary.start_time} 至 ${summary.end_time}`], ["請假時數", formatLeaveDuration(summary.requested_days)],
      ["原因", summary.reason], ["附件", summary.attachment_name || "無"],
    ];
    return `<section class="summary-card"><h2>請確認請假內容</h2><div class="summary-grid">${rows.map(([label, value]) => `<div class="summary-item"><span>${hrEscapeHtml(label)}</span><strong>${hrEscapeHtml(value)}</strong></div>`).join("")}</div><div class="summary-actions"><button class="button primary confirm-draft" type="button">確認送出</button><button class="button secondary edit-draft" type="button">修改內容</button></div></section>`;
  }

  async function previewMessage(text) {
    const parsed = parseLeaveMessage(text, state.leaveTypes);
    if (parsed.missing.length) {
      appendMessage("assistant", `還需要提供${parsed.missing.join("、")}。請重新輸入完整內容，例如：「我要請 9 月 3 日特休，原因是處理私人事務」。`);
      return;
    }
    const file = document.querySelector("#assistantAttachment").files[0];
    const attachment = await encodeAttachment(file);
    const preview = await apiRequest("/leave-assistant/preview/", {
      method: "POST",
      body: JSON.stringify({ ...parsed.payload, ...attachment }),
    });
    state.draftId = preview.draft_id;
    const bubble = appendMessage("assistant", summaryHtml(preview.summary), { html: true });
    bubble.querySelector(".confirm-draft").addEventListener("click", () => submitDraft(bubble));
    bubble.querySelector(".edit-draft").addEventListener("click", () => {
      state.draftId = null;
      bubble.querySelector(".summary-actions").remove();
      appendMessage("assistant", "好的，請在下方重新輸入要修改的完整內容。原草稿不會送出。 ");
      document.querySelector("#assistantInput").focus();
    });
  }

  async function submitDraft(bubble) {
    const button = bubble.querySelector(".confirm-draft");
    button.disabled = true;
    button.textContent = "送出中…";
    try {
      const result = await apiRequest("/leave-assistant/submit/", {
        method: "POST",
        body: JSON.stringify({ draft_id: state.draftId }),
      });
      bubble.querySelector(".summary-actions").innerHTML = `<div class="assistant-success">申請已送出，編號 ${hrEscapeHtml(result.request.request_number)}</div>`;
      appendMessage("assistant", `請假申請已建立，目前狀態為「${result.request.status_label}」。你可以到請假紀錄查看後續審核結果。`);
      state.draftId = null;
      document.querySelector("#assistantAttachment").value = "";
      document.querySelector("#attachmentName").textContent = "支援 PDF、JPG、PNG，最大 2 MB";
    } catch (error) {
      button.disabled = false;
      button.textContent = "確認送出";
      appendMessage("assistant", error.message || "目前無法送出申請，請稍後再試。 ");
    }
  }

  function setupVoiceInput() {
    const VoiceRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const button = document.querySelector("#voiceButton");
    if (!VoiceRecognition) {
      button.disabled = true;
      button.title = "此瀏覽器不支援語音輸入";
      return;
    }
    state.recognition = new VoiceRecognition();
    state.recognition.lang = "zh-TW";
    state.recognition.interimResults = false;
    state.recognition.onstart = () => { button.classList.add("listening"); button.textContent = "■"; };
    state.recognition.onend = () => { button.classList.remove("listening"); button.textContent = "🎤"; };
    state.recognition.onerror = () => appendMessage("assistant", "沒有收到清楚的語音，請再試一次或改用文字輸入。 ");
    state.recognition.onresult = (event) => {
      document.querySelector("#assistantInput").value = event.results[0][0].transcript;
    };
    button.addEventListener("click", () => state.recognition.start());
  }

  async function initialize() {
    if (!localStorage.getItem("hr_token")) {
      window.location.href = "../login.html?next=employee/leave-assistant.html";
      return;
    }
    try {
      const [user, typePayload] = await Promise.all([getCurrentUser(), apiRequest("/leave-types/")]);
      state.user = user;
      state.leaveTypes = (Array.isArray(typePayload) ? typePayload : typePayload.results || []).filter((item) => item.is_active);
      const bubble = appendMessage("assistant", `你好，${user.display_name || user.username}。請告訴我要請什麼假、日期和原因，我會先整理成摘要讓你確認。`);
      addSuggestions(bubble);
      setupVoiceInput();
    } catch (error) {
      appendMessage("assistant", error.message || "無法載入請假服務。 ");
    }
  }

  document.querySelector("#assistantForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = document.querySelector("#assistantInput");
    const text = input.value.trim();
    if (!text) return;
    appendMessage("user", text);
    input.value = "";
    const button = event.currentTarget.querySelector("button[type=submit]");
    button.disabled = true;
    try { await previewMessage(text); }
    catch (error) { appendMessage("assistant", error.message || "無法理解或驗證這筆請假內容，請重新輸入。 "); }
    finally { button.disabled = false; }
  });

  document.querySelector("#assistantAttachment").addEventListener("change", (event) => {
    document.querySelector("#attachmentName").textContent = event.target.files[0]?.name || "支援 PDF、JPG、PNG，最大 2 MB";
  });

  window.parseLeaveMessage = parseLeaveMessage;
  initialize();
})();
