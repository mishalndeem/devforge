const chatToggle = document.getElementById("chat-toggle");
const chatContainer = document.getElementById("chat-container");
const closeChat = document.getElementById("close-chat");
const minimizeChat = document.getElementById("minimize-chat");

const messages = document.getElementById("chat-messages");
const sendBtn = document.getElementById("send-btn");
const input = document.getElementById("message-input");
const suggestionsDiv = document.getElementById("suggested-questions");

// Change this after deployment
const API_URL = "http://127.0.0.1:8000/chat";

let sessionId = localStorage.getItem("session_id");
//2
chatToggle.addEventListener("click", () => {

    chatContainer.classList.remove("hidden");

});

closeChat.addEventListener("click", () => {

    chatContainer.classList.add("hidden");

});

if (minimizeChat) {

    minimizeChat.addEventListener("click", () => {

        chatContainer.classList.add("hidden");

    });

}
//3
function addMessage(sender, text, sources = []) {

    const wrapper = document.createElement("div");

    wrapper.className = `message ${sender}`;

    const bubble = document.createElement("div");

    bubble.className = "bubble";

    bubble.innerText = text;

    wrapper.appendChild(bubble);

    // Sources
    if (sources.length > 0) {

        const source = document.createElement("div");

        source.className = "source";

        source.innerText = "📚 Source: " + sources.join(", ");

        wrapper.appendChild(source);

    }

    messages.appendChild(wrapper);

    messages.scrollTop = messages.scrollHeight;

}
//4
function welcome() {

    if(messages.children.length > 0)
        return;

    addMessage(

        "bot",

`👋 Welcome to Rashid Dental Clinic!

I'm your AI Assistant.

I can help with:

• Dental services
• Opening hours
• Appointments
• Clinic location

I cannot diagnose dental conditions or prescribe medication.`

    );

}

welcome();
//5
let typingDiv = null;

function showTyping() {

    typingDiv = document.createElement("div");

    typingDiv.className = "message bot";

    typingDiv.innerHTML = `

        <div class="bubble">

            Typing...

        </div>

    `;

    messages.appendChild(typingDiv);

    messages.scrollTop = messages.scrollHeight;

}

function hideTyping(){

    if(typingDiv){

        typingDiv.remove();

        typingDiv = null;

    }

}
//6
async function sendMessage(){

    const text = input.value.trim();

    if(text === "")
        return;

    addMessage("user", text);

    input.value = "";

    showTyping();

    try{

        const response = await fetch(API_URL,{

            method:"POST",

            headers:{
                "Content-Type":"application/json"
            },

            body:JSON.stringify({

                session_id:sessionId,

                message:text

            })

        });

        const data = await response.json();

        hideTyping();

        sessionId = data.session_id;

        localStorage.setItem("session_id", sessionId);

        addMessage(

            "bot",

            data.message,

            data.sources

        );

        renderSuggestions(data.suggestions);

    }

    catch(error){

        hideTyping();

        addMessage(

            "bot",

            "Unable to connect to the AI assistant."

        );

        console.error(error);

    }

}
//7
sendBtn.addEventListener("click", sendMessage);

input.addEventListener("keypress",(e)=>{

    if(e.key==="Enter")

        sendMessage();

});
//8
// Purely cosmetic: picks an icon to prefix a suggestion label based on
// keywords. Does not change what gets sent to the backend.
function iconFor(question){

    const q = question.toLowerCase();

    if (q.includes("appoint") || q.includes("book")) return "🗓️";
    if (q.includes("service"))                       return "💼";
    if (q.includes("location") || q.includes("hour")) return "📍";
    if (q.includes("emergency"))                      return "⚠️";

    return "💬";

}

function renderSuggestions(list){

    suggestionsDiv.innerHTML="";

    list.forEach(question=>{

        const button=document.createElement("button");

        button.className="suggestion";

        button.innerHTML = `<span>${iconFor(question)}</span><span>${question}</span>`;

        button.onclick=()=>{

            input.value=question;

            sendMessage();

        };

        suggestionsDiv.appendChild(button);

    });

}
//9
renderSuggestions([

"Book Appointment",

"Our Services",

"Location & Hours",

"Emergency Care"

]);