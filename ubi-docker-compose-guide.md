
# 🐳 Running Red Hat UBI with Docker Compose

This guide sets up a Red Hat UBI 9 container and opens an interactive shell using Docker Compose.

---

## 📁 `docker-compose.yml`

```yaml
version: '3.8'

services:
  ubi:
    image: registry.access.redhat.com/ubi9/ubi:latest
    container_name: ubi9-shell
    stdin_open: true            # Keep STDIN open even if not attached
    tty: true                   # Allocate a pseudo-TTY
    command: /bin/bash          # Start an interactive shell
    working_dir: /workspace
    volumes:
      - .:/workspace            # Mount current directory into the container
```

---

## ▶️ How to Use

1. Save this file as `docker-compose.yml`.
2. Open a terminal and run:

```bash
docker-compose up
```

3. You will enter an interactive shell:
```
[root@container-id /workspace]#
```

---

## 🔁 Alternative Command (Direct Terminal)

To run once and drop into the shell:

```bash
docker-compose run ubi
```

---

## ⚙️ Optional: Build from a Custom Dockerfile

To add tools (e.g., `curl`, `pip`), update the `docker-compose.yml`:

```yaml
    build:
      context: .
      dockerfile: Dockerfile
```

Then add your `Dockerfile` in the same directory.

---

Happy Hacking! 🧪
