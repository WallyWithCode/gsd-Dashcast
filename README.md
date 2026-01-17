# Dashcast

A Dockerized webhook service that receives RTSP stream URLs via webhook payload and casts them to Google Cast devices with device-specific endpoints and confirmed streaming responses.

## Features

- 🎯 **Device-specific webhook endpoints** - Each Cast device gets its own webhook URL
- ✅ **Confirmed streaming responses** - Webhook only responds when video is actively streaming
- 🐳 **Simple Docker deployment** - Single command setup with Docker Compose
- 🔒 **Optional webhook authentication** - Secret key protection for webhooks
- 📊 **Health monitoring** - Built-in health checks and device discovery
- 🌐 **RTSP/RTMP/HTTP support** - Multiple stream protocol compatibility

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/WallyWithCode/gsd-Dashcast.git
cd gsd-Dashcast
```

### 2. Configure (Optional)

```bash
# Copy environment template
cp .env.example .env

# Edit with your webhook secret and preferences
nano .env
```

### 3. Start the Service

```bash
# Super simple - just one command!
docker-compose up -d
```

That's it! 🎉 Your Dashcast service is now running on `http://localhost:8080`

## Usage

### Discover Devices

```bash
curl http://localhost:8080/devices
```

### Cast to a Device

```bash
# Cast to "Living Room TV"
curl -X POST http://localhost:8080/cast/Living%20Room%20TV \
  -H "Content-Type: application/json" \
  -d '{"rtsp_url": "rtsp://example.com/stream.mp4"}'

# Or use the webhook endpoint
curl -X POST http://localhost:8080/webhook/Living%20Room%20TV \
  -H "Content-Type: application/json" \
  -d '{"rtsp_url": "rtsp://example.com/stream.mp4"}'
```

### With Webhook Secret (if configured)

```bash
curl -X POST http://localhost:8080/cast/Living%20Room%20TV \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: your-secret-key-here" \
  -d '{"rtsp_url": "rtsp://example.com/stream.mp4"}'
```

## Response Format

### Success (Streaming Confirmed)
```json
{
  "status": "success",
  "device": "Living Room TV",
  "message": "Streaming confirmed on Living Room TV",
  "streaming": true
}
```

### Error
```json
{
  "status": "error",
  "device": "Living Room TV",
  "message": "Device not found",
  "streaming": false
}
```

## Configuration

### Environment Variables (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `WEBHOOK_SECRET` | none | Optional secret key for webhook authentication |
| `CAST_TIMEOUT` | 30 | Seconds to wait for streaming confirmation |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Device Configuration

Devices are automatically discovered on your local network. If you need to specify static IP addresses, edit `config/devices.conf`:

```bash
# LIVING_ROOM_TV=192.168.1.100
# BEDROOM_TV=192.168.1.101
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health check |
| GET | `/devices` | List all discovered Cast devices |
| POST | `/cast/<device_name>` | Cast stream to specific device |
| POST | `/webhook/<device_name>` | Alias for `/cast/<device_name>` |

## How It Works

1. **Webhook Reception**: Receives RTSP URL via POST request
2. **Device Discovery**: Automatically discovers Cast devices on network
3. **Stream Validation**: Validates RTSP/RTMP/HTTP URL format
4. **Casting**: Connects to Cast device and starts stream
5. **Confirmation**: Waits and verifies video is actively streaming
6. **Response**: Returns success only after streaming confirmation

## Security

- Optional webhook secret authentication
- URL validation for stream sources
- Network isolation within Docker container
- No persistent storage of stream URLs

## Development

### Building from Source

```bash
docker build -t dashcast .
```

### Running Tests

```bash
# Check service health
curl http://localhost:8080/health

# Test device discovery
curl http://localhost:8080/devices
```

## Troubleshooting

### Common Issues

1. **"Device not found"**
   - Ensure Cast device is on same network
   - Check device is powered on and connected
   - Wait 30 seconds for auto-discovery

2. **"Stream failed to start"**
   - Verify RTSP URL is accessible
   - Check stream format compatibility
   - Ensure device supports the stream format

3. **Connection Issues**
   - Check Docker container is running
   - Verify port 8080 is accessible
   - Check network connectivity

### Logs

```bash
# View service logs
docker-compose logs -f

# View specific logs
docker-compose logs dashcast
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is open source and available under the [MIT License](LICENSE).

## Support

- 📖 [Documentation](https://github.com/WallyWithCode/gsd-Dashcast/wiki)
- 🐛 [Issues](https://github.com/WallyWithCode/gsd-Dashcast/issues)
- 💬 [Discussions](https://github.com/WallyWithCode/gsd-Dashcast/discussions)

---

**Dashcast** - Making RTSP to Google Cast streaming as simple as sending a webhook request. 🚀