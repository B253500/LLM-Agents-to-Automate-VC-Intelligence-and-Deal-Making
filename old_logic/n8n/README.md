# n8n Automation Hub

This directory contains all n8n workflows and automation configurations for the VC Agents project.

## 🏗️ Structure

```
n8n/
├── docker-compose.yml          # Docker configuration for n8n
├── Dockerfile                  # Custom n8n image with Python/Playwright
├── data/                       # n8n data persistence (workflows, logs, etc.)
├── workflows/                  # Organized workflow directories
│   ├── email_assistant/        # Email automation workflows
│   └── web_scraping/          # Web scraping automation workflows
└── README.md                  # This file
```

## 🚀 Quick Start

### 1. Start n8n with Docker
```bash
cd n8n
docker-compose up -d
```

### 2. Access n8n Web Interface
- **URL**: http://localhost:5678
- **Username**: `<your-user>` (configured in docker-compose.yml)
- **Password**: `<your-password>` (configured in docker-compose.yml)

### 3. Import Workflows
- Navigate to Settings → Import/Export
- Import workflow files from `workflows/` directories

## 🔧 Configuration

### Environment Variables
Update `docker-compose.yml` with your credentials:
```yaml
environment:
  - N8N_BASIC_AUTH_USER=your-username
  - N8N_BASIC_AUTH_PASSWORD=your-password
```

### Volume Mounts
- `./data:/home/node/.n8n` - n8n data persistence
- `../:/home/node/project` - Access to project files

## 📋 Workflows

### Email Assistant Workflows
Location: `workflows/email_assistant/`
- **Email Processing**: Automatically process incoming emails
- **Memo Generation**: Trigger investment memo creation
- **PDF Generation**: Convert memos to PDF format
- **Notification**: Send results via email

### Web Scraping Workflows
Location: `workflows/web_scraping/`
- **Report Discovery**: Find new reports on websites
- **Automated Downloads**: Download reports automatically
- **Data Processing**: Process downloaded content
- **Storage Management**: Organize downloaded files

## 🛠️ Custom Docker Image

The `Dockerfile` creates a custom n8n image with:
- **Python 3**: For custom Python scripts
- **Playwright**: For web scraping capabilities
- **Browser Support**: Chrome, Firefox, WebKit

## 📊 Monitoring

### Logs
```bash
# View n8n logs
docker-compose logs -f n8n

# View specific workflow logs
docker exec -it n8n-n8n-1 tail -f /home/node/.n8n/logs/
```

### Data Persistence
- **Database**: `data/database.sqlite`
- **Workflows**: `data/workflows/`
- **Credentials**: `data/credentials/`
- **Logs**: `data/logs/`

## 🔄 Workflow Development

### Creating New Workflows
1. Design workflow in n8n web interface
2. Export workflow to `workflows/[category]/`
3. Document workflow purpose and triggers

### Testing Workflows
1. Use n8n's built-in testing tools
2. Monitor execution logs
3. Validate data flow between nodes

## 🚨 Troubleshooting

### Common Issues
1. **Port conflicts**: Change port in `docker-compose.yml`
2. **Permission issues**: Check volume mount permissions
3. **Python scripts**: Ensure scripts are in mounted project directory

### Debug Mode
```bash
# Run with debug logging
docker-compose down
docker-compose up -d --build
```

## 📈 Scaling

### Multiple Workflows
- Organize workflows by category in `workflows/`
- Use consistent naming conventions
- Document dependencies between workflows

### Performance
- Monitor resource usage: `docker stats`
- Optimize workflow execution times
- Use appropriate scheduling intervals

## 🔐 Security

### Authentication
- Change default credentials in `docker-compose.yml`
- Use environment variables for sensitive data
- Regularly update n8n version

### Data Protection
- Backup `data/` directory regularly
- Secure access to n8n web interface
- Monitor workflow execution logs

## 📚 Resources

- [n8n Documentation](https://docs.n8n.io/)
- [n8n Community](https://community.n8n.io/)
- [Docker Compose Guide](https://docs.docker.com/compose/) 