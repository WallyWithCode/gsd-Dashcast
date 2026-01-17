# Dashcast

## What This Is

A Dockerized webhook service that receives RTSP stream URLs via webhook payload and casts them to Google Cast devices with device-specific endpoints and low latency.

## Core Value

Simple webhook API that just works - device-specific endpoints that accept RTSP URLs and stream to Google Cast reliably.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Docker containerized service deployment
- [ ] Webhook endpoints for different Google Cast devices
- [ ] RTSP stream URL acceptance via webhook payload
- [ ] Low-latency RTSP to Google Cast streaming
- [ ] Google Cast device communication and casting
- [ ] Stream format compatibility for Cast devices
- [ ] Basic error handling and health checking

### Out of Scope

- Web management UI — webhook API only, no graphical interface
- Stream recording or storage — live casting only

## Context

- Target environment: Docker containers (Docker-only deployment constraint)
- Integration: Automation systems via webhook triggers
- Technical challenge: RTSP stream processing and Google Cast protocol implementation
- Performance requirement: Low latency streaming from webhook receipt to device casting

## Constraints

- **Deployment**: Docker-only — Must run in containers, no bare metal deployment
- **API Design**: Device-specific endpoints — Each Cast device gets its own webhook endpoint

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Device-specific endpoints | Simplifies API design, each endpoint maps to one Cast device | — Pending |
| RTSP URL in webhook body | Flexible approach, allows dynamic stream sources | — Pending |
| Webhook-only API | Fits automation use cases, no UI complexity | — Pending |

---
*Last updated: 2026-01-17 after initialization*