import sqlite3, sys, bcrypt
email, password = sys.argv[1], sys.argv[2]
h = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
c = sqlite3.connect("garbage.db")
n = c.execute("UPDATE users SET hashed_password=? WHERE email=?", (h, email.lower())).rowcount
c.execute("UPDATE refresh_tokens SET revoked=1 WHERE user_id=(SELECT id FROM users WHERE email=?)", (email.lower(),))
c.commit()
print("updated", n)
