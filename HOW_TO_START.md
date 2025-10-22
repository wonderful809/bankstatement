# 🚀 How to Start the SaaS Platform

## ❌ Why "Connection Refused"?

The server isn't running yet! You need to **start the Flask server** first.

---

## ✅ How to Start the Server

### Method 1: Using the Run Script (Easiest)

Open a terminal in the `/workspace` directory and run:

```bash
python3 RUN_SERVER.py
```

**That's it!** The server will start and show you the URL.

---

### Method 2: Direct Command

```bash
cd /workspace
python3 app_bankstatement_saas.py
```

---

### Method 3: Using the Shell Script

```bash
cd /workspace
./start_preview.sh
```

---

## 📍 Where to Access

Once the server is running, open your browser and go to:

- **http://localhost:5000** (recommended)
- **http://127.0.0.1:5000** (alternative)
- **http://0.0.0.0:5000** (if the above don't work)

---

## 👤 Login Credentials

**Demo Account:**
- Email: `demo@example.com`
- Password: `demo123`

---

## 🖥️ Step-by-Step Instructions

### Step 1: Open Terminal
- Open a terminal/command prompt
- Navigate to the workspace directory:
  ```bash
  cd /workspace
  ```

### Step 2: Start the Server
Run one of these commands:
```bash
# Option A (Recommended)
python3 RUN_SERVER.py

# Option B
python3 app_bankstatement_saas.py
```

### Step 3: Wait for Startup
You should see output like:
```
 * Running on http://0.0.0.0:5000
 * Running on http://127.0.0.1:5000
```

### Step 4: Open Browser
Once you see the "Running on" messages, open:
**http://localhost:5000**

---

## 🐛 Troubleshooting

### "Port 5000 is already in use"

**Solution 1:** Kill the existing process
```bash
# On Linux/Mac
lsof -ti:5000 | xargs kill -9

# On Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

**Solution 2:** Use a different port
```bash
export FLASK_PORT=5001
python3 app_bankstatement_saas.py
# Then visit http://localhost:5001
```

### "Module not found"

Install dependencies:
```bash
pip install -r requirements.txt
```

### "Can't connect to localhost"

1. Make sure the server is actually running (check terminal output)
2. Try http://127.0.0.1:5000 instead
3. Check if your firewall is blocking port 5000
4. Try a different browser

### Still having issues?

Check the terminal output for error messages. The issue is usually:
- Server not started
- Wrong port number
- Firewall blocking
- Dependencies missing

---

## ✅ Verification Checklist

Before opening the browser, make sure:

- [ ] Terminal shows "Running on http://..."
- [ ] No error messages in terminal
- [ ] Port 5000 is not being used by another app
- [ ] You're using the correct URL (localhost:5000)

---

## 📺 What You Should See

### In Terminal:
```
════════════════════════════════════════════════════════════
Starting Flask development server...
════════════════════════════════════════════════════════════
 * Serving Flask app 'app_bankstatement_saas'
 * Debug mode: on
 * Running on http://0.0.0.0:5000
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

### In Browser:
Beautiful landing page with:
- Hero section
- Feature cards
- Pricing button
- Sign up / Login buttons

---

## 🎯 Quick Test

Once server is running:

1. Open http://localhost:5000
2. Click "Login"
3. Use demo@example.com / demo123
4. See the dashboard!

---

## ⏸️ How to Stop the Server

Press **Ctrl+C** in the terminal where the server is running.

---

## 💡 Pro Tips

1. **Keep Terminal Open**: Don't close the terminal while using the app
2. **Check Logs**: Terminal shows all requests and errors
3. **Restart if Needed**: Ctrl+C then run the command again
4. **Use Incognito**: For clean testing without cached data

---

## 📱 Alternative: Access from Another Device

If you want to access from phone/tablet on same network:

1. Find your computer's IP address:
   ```bash
   # On Linux/Mac
   ifconfig | grep inet
   
   # On Windows
   ipconfig
   ```

2. Use that IP instead of localhost:
   ```
   http://YOUR-IP-ADDRESS:5000
   ```

---

## 🆘 Still Need Help?

### Check These:

1. **Is Python installed?**
   ```bash
   python3 --version
   ```

2. **Are dependencies installed?**
   ```bash
   pip list | grep Flask
   ```

3. **Is the database created?**
   ```bash
   ls -la /workspace/*.db
   ```

4. **Is port 5000 free?**
   ```bash
   lsof -i :5000
   ```

---

## ✨ Remember

**The server MUST be running for the website to work!**

Think of it like:
- ❌ Trying to visit a website when the server is off = Connection Refused
- ✅ Server running = Website accessible

---

**Ready? Run this now:**

```bash
cd /workspace
python3 RUN_SERVER.py
```

Then open: **http://localhost:5000** 🚀
