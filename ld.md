# 📘 LD Cheat Sheet for Dynatrace DQL Parsing

This guide maps **common log patterns** (often extracted in Splunk with `rex`) into **Dynatrace DQL `parse` patterns** using the `LD` (Literal Delimiter) operator.  

---

## 🔎 What is `LD`?
- **LD = Literal Delimiter**  
- It anchors on **fixed text in a log message**.  
- It does not capture itself — only the value **after** the literal is extracted.  

---

## 🧩 Syntax
```dql
parse content, "LD '<literal>' <TYPE:fieldname>"
