const form = document.getElementById("auth-form");
const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");
const errorBox = document.getElementById("auth-error");
const submitBtn = document.getElementById("auth-submit");

let mode = "login"; // or "register"

function setMode(next) {
  mode = next;
  const isLogin = mode === "login";
  document.getElementById("auth-title").textContent = isLogin ? "Welcome back" : "Create your account";
  document.getElementById("auth-subtitle").textContent = isLogin
    ? "Sign in to check your emails for spam."
    : "It only takes a few seconds to get started.";
  submitBtn.textContent = isLogin ? "Sign in" : "Create account";
  document.getElementById("switch-text").textContent = isLogin
    ? "Don't have an account?"
    : "Already have an account?";
  document.getElementById("switch-mode").textContent = isLogin ? "Create one" : "Sign in";
  document.getElementById("password-hint").hidden = isLogin;
  passwordInput.autocomplete = isLogin ? "current-password" : "new-password";
  errorBox.hidden = true;
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
}

// FastAPI returns either a string or a list of validation errors in "detail"
function errorMessage(body) {
  if (!body || !body.detail) return "Something went wrong. Please try again.";
  if (typeof body.detail === "string") return body.detail;
  const field = body.detail[0] && body.detail[0].loc && body.detail[0].loc.slice(-1)[0];
  if (field === "email") return "Enter a valid email address.";
  if (field === "password") return "Password must be 8 to 72 characters.";
  return "Please check your details and try again.";
}

const toggleBtn = document.getElementById("toggle-password");
toggleBtn.addEventListener("click", () => {
  const show = passwordInput.type === "password";
  passwordInput.type = show ? "text" : "password";
  toggleBtn.textContent = show ? "Hide" : "Show";
  toggleBtn.setAttribute("aria-label", show ? "Hide password" : "Show password");
});

document.getElementById("switch-mode").addEventListener("click", () => {
  setMode(mode === "login" ? "register" : "login");
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.hidden = true;

  const email = emailInput.value.trim();
  const password = passwordInput.value;
  if (!email || !password) {
    showError("Enter your email and password.");
    return;
  }
  if (mode === "register" && password.length < 8) {
    showError("Password must be at least 8 characters.");
    return;
  }

  submitBtn.disabled = true;
  try {
    const res = await fetch(`/auth/${mode}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (res.ok) {
      window.location.href = "/";
      return;
    }
    showError(errorMessage(await res.json().catch(() => null)));
  } catch {
    showError("Can't reach the server. Is it running?");
  } finally {
    submitBtn.disabled = false;
  }
});
