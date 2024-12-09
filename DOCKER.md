# Docker Usage Instructions

## Building and Running

1. Build the container:
```bash
docker-compose build
```

2. Start a shell session:
```bash
docker-compose run --rm repo-to-text
```

Once in the shell, you can run repo-to-text:
```bash
# Process current directory
repo-to-text

# Process specific directory
repo-to-text /home/user/myproject

# Use with options
repo-to-text --output-dir /home/user/output
```

The container mounts your home directory at `/home/user`, allowing access to all your projects.
