import os
import logging
import json
import threading
import time
from flask import Flask, request, jsonify
from pychromecast import Chromecast, get_chromecasts
from pychromecast.controllers.media import MediaController
import requests
from urllib.parse import urlparse
import signal
import sys

app = Flask(__name__)

# Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
CAST_TIMEOUT = int(os.getenv('CAST_TIMEOUT', 30))
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', None)

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CastManager:
    def __init__(self):
        self.active_casts = {}
        self.discover_devices()
        
    def discover_devices(self):
        """Discover all available Cast devices on the network"""
        try:
            logger.info("Discovering Cast devices...")
            chromecasts = get_chromecasts()
            for cc in chromecasts:
                self.active_casts[cc.name] = {
                    'device': cc,
                    'status': 'discovered',
                    'last_seen': time.time()
                }
                logger.info(f"Found Cast device: {cc.name}")
            return list(self.active_casts.keys())
        except Exception as e:
            logger.error(f"Error discovering devices: {e}")
            return []
    
    def get_device(self, device_name):
        """Get a specific Cast device by name"""
        if device_name not in self.active_casts:
            # Refresh discovery
            self.discover_devices()
            
        if device_name in self.active_casts:
            return self.active_casts[device_name]['device']
        return None
    
    def wait_for_streaming_status(self, device, timeout=CAST_TIMEOUT):
        """Wait for device to start streaming before returning success"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check if device is actively playing media
                if hasattr(device, 'media_controller') and device.media_controller.status:
                    status = device.media_controller.status
                    if status.player_state in ['PLAYING', 'BUFFERING']:
                        logger.info(f"Device {device.name} is streaming (state: {status.player_state})")
                        return True
                
                # Check device app status
                if hasattr(device, 'status') and device.status:
                    if device.status.app_id and device.status.app_id != 'E8C28D3C':
                        logger.info(f"Device {device.name} has active app: {device.status.app_id}")
                        return True
                        
            except Exception as e:
                logger.debug(f"Status check error for {device.name}: {e}")
            
            time.sleep(1)
        
        logger.warning(f"Device {device.name} did not start streaming within {timeout} seconds")
        return False
    
    def cast_rtsp_stream(self, device_name, rtsp_url):
        """Cast RTSP stream to device and wait for streaming confirmation"""
        device = self.get_device(device_name)
        if not device:
            logger.error(f"Cast device '{device_name}' not found")
            return False, "Device not found"
        
        try:
            logger.info(f"Connecting to Cast device: {device_name}")
            device.wait()
            
            # Create media controller
            media_controller = MediaController()
            device.register_handler(media_controller)
            
            # Convert RTSP to HTTP stream format for Cast
            # Note: In production, you might need a transcoder service
            stream_url = rtsp_url  # For now, assume direct casting
            
            logger.info(f"Casting stream to {device_name}: {stream_url}")
            
            # Start casting
            media_controller.play_media(
                stream_url,
                'video/mp4'  # May need adjustment based on RTSP format
            )
            
            # Block until streaming is confirmed
            streaming_confirmed = self.wait_for_streaming_status(device)
            
            if streaming_confirmed:
                logger.info(f"✅ Stream confirmed active on {device_name}")
                return True, f"Streaming confirmed on {device.name}"
            else:
                logger.error(f"❌ Stream failed to start on {device_name}")
                return False, f"Stream failed to start on {device.name}"
                
        except Exception as e:
            logger.error(f"Error casting to {device_name}: {e}")
            return False, f"Casting error: {str(e)}"

cast_manager = CastManager()

def validate_webhook_secret(request):
    """Validate webhook secret if configured"""
    if WEBHOOK_SECRET:
        provided_secret = request.headers.get('X-Webhook-Secret')
        if provided_secret != WEBHOOK_SECRET:
            return False
    return True

def validate_rtsp_url(url):
    """Basic validation of RTSP URL"""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ['rtsp', 'rtmp', 'http', 'https'] and bool(parsed.netloc)
    except:
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'devices': len(cast_manager.active_casts),
        'timestamp': time.time()
    })

@app.route('/devices', methods=['GET'])
def list_devices():
    """List all available Cast devices"""
    devices = cast_manager.discover_devices()
    return jsonify({
        'devices': devices,
        'count': len(devices)
    })

@app.route('/cast/<device_name>', methods=['POST'])
def cast_to_device(device_name):
    """Cast RTSP stream to specific device"""
    if not validate_webhook_secret(request):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    if not data or 'rtsp_url' not in data:
        return jsonify({'error': 'rtsp_url required in request body'}), 400
    
    rtsp_url = data['rtsp_url']
    if not validate_rtsp_url(rtsp_url):
        return jsonify({'error': 'Invalid RTSP URL'}), 400
    
    logger.info(f"Received webhook request to cast {rtsp_url} to {device_name}")
    
    # Cast and wait for streaming confirmation
    success, message = cast_manager.cast_rtsp_stream(device_name, rtsp_url)
    
    if success:
        return jsonify({
            'status': 'success',
            'device': device_name,
            'message': message,
            'streaming': True
        })
    else:
        return jsonify({
            'status': 'error',
            'device': device_name,
            'message': message,
            'streaming': False
        }), 500

@app.route('/webhook/<device_name>', methods=['POST'])
def webhook_endpoint(device_name):
    """Generic webhook endpoint (alias for /cast)"""
    return cast_to_device(device_name)

if __name__ == '__main__':
    # Discover devices on startup
    logger.info("Starting Dashcast webhook server...")
    devices = cast_manager.discover_devices()
    logger.info(f"Found {len(devices)} Cast devices: {', '.join(devices)}")
    
    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=8080,
        debug=False,
        threaded=True
    )