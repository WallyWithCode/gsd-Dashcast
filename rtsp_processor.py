import os
import logging
import tempfile
import threading
import time
import subprocess
import json
import uuid
from urllib.parse import urlparse
import ffmpeg

logger = logging.getLogger(__name__)

class RTSPProcessor:
    def __init__(self, temp_dir="/tmp/dashcast"):
        self.temp_dir = temp_dir
        self.active_streams = {}
        self.stream_locks = {}
        
        # Create temp directory if it doesn't exist
        os.makedirs(temp_dir, exist_ok=True)
        
    def validate_rtsp_url(self, url):
        """Validate RTSP/RTMP/HTTP stream URL"""
        try:
            parsed = urlparse(url)
            valid_schemes = ['rtsp', 'rtmp', 'http', 'https']
            return parsed.scheme in valid_schemes and bool(parsed.netloc)
        except Exception as e:
            logger.error(f"URL validation error: {e}")
            return False
    
    def test_stream_connectivity(self, url, timeout=10):
        """Test if we can connect to the RTSP stream"""
        try:
            logger.info(f"Testing connectivity to: {url}")
            
            # Use FFprobe to check stream
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'stream=codec_name,width,height,avg_frame_rate',
                '-of', 'json',
                '-timeout', str(timeout * 1000000),  # microseconds
                url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            
            if result.returncode == 0:
                probe_data = json.loads(result.stdout)
                if probe_data.get('streams'):
                    video_stream = next((s for s in probe_data['streams'] if s['codec_type'] == 'video'), None)
                    if video_stream:
                        logger.info(f"Stream validated: {video_stream.get('codec_name')} {video_stream.get('width')}x{video_stream.get('height')}")
                        return True, video_stream
            
            logger.error(f"Stream probe failed: {result.stderr}")
            return False, None
            
        except subprocess.TimeoutExpired:
            logger.error(f"Stream connection timeout after {timeout}s")
            return False, None
        except Exception as e:
            logger.error(f"Stream connectivity test failed: {e}")
            return False, None
    
    def convert_to_hls(self, rtsp_url, output_path, segment_time=2):
        """Convert RTSP stream to HLS format for Cast compatibility"""
        try:
            logger.info(f"Converting RTSP to HLS: {rtsp_url} -> {output_path}")
            
            # Create HLS output directory
            hls_dir = os.path.dirname(output_path)
            os.makedirs(hls_dir, exist_ok=True)
            
            # FFmpeg command for RTSP to HLS conversion
            (
                ffmpeg
                .input(rtsp_url, 
                    rtsp_transport='tcp',
                    rtsp_flags='prefer_tcp',
                    fflags='nobuffer',
                    analyzeduration='10000000',
                    probesize='1000000')
                .output(
                    output_path,
                    vcodec='libx264',
                    acodec='aac',
                    format='hls',
                    hls_time=segment_time,
                    hls_list_size=3,
                    hls_flags='delete_segments+append_list',
                    hls_segment_type='mpegts',
                    hls_segment_filename=f'{hls_dir}/segment_%03d.ts',
                    g=60,  # GOP size
                    preset='fast',
                    crf=23,
                    movflags='frag_keyframe+empty_moov'
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            logger.info(f"HLS conversion successful: {output_path}")
            return True, None
            
        except ffmpeg.Error as e:
            error_msg = f"FFmpeg HLS conversion failed: {e.stderr.decode()}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"HLS conversion error: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def convert_to_dash(self, rtsp_url, output_path):
        """Convert RTSP stream to DASH format for Cast compatibility"""
        try:
            logger.info(f"Converting RTSP to DASH: {rtsp_url} -> {output_path}")
            
            dash_dir = os.path.dirname(output_path)
            os.makedirs(dash_dir, exist_ok=True)
            
            (
                ffmpeg
                .input(rtsp_url,
                    rtsp_transport='tcp',
                    rtsp_flags='prefer_tcp',
                    fflags='nobuffer')
                .output(
                    output_path,
                    vcodec='libx264',
                    acodec='aac',
                    format='dash',
                    window_size=3,
                    extra_window_size=1,
                    seg_duration=3,
                    frag_duration=1,
                    target_latency=5,
                    streaming=1,
                    remove_at_exit=1
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            logger.info(f"DASH conversion successful: {output_path}")
            return True, None
            
        except ffmpeg.Error as e:
            error_msg = f"FFmpeg DASH conversion failed: {e.stderr.decode()}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"DASH conversion error: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def create_local_http_server(self, stream_dir, port=0):
        """Create a local HTTP server to serve HLS/DASH segments"""
        try:
            import http.server
            import socketserver
            from threading import Thread
            
            # Find an available port
            if port == 0:
                with socketserver.TCPServer(("localhost", 0), http.server.SimpleHTTPRequestHandler) as s:
                    port = s.server_address[1]
            
            handler = http.server.SimpleHTTPRequestHandler
            httpd = socketserver.TCPServer(("localhost", port), handler)
            
            # Change to stream directory
            os.chdir(stream_dir)
            
            # Start server in a separate thread
            server_thread = Thread(target=httpd.serve_forever, daemon=True)
            server_thread.start()
            
            logger.info(f"Local HTTP server started on port {port} for {stream_dir}")
            return f"http://localhost:{port}", httpd, server_thread
            
        except Exception as e:
            logger.error(f"Failed to start HTTP server: {e}")
            return None, None, None
    
    def process_stream_for_cast(self, rtsp_url, device_name=None):
        """Process RTSP stream for Cast device compatibility"""
        stream_id = str(uuid.uuid4())
        stream_dir = os.path.join(self.temp_dir, stream_id)
        
        try:
            os.makedirs(stream_dir, exist_ok=True)
            
            # Test stream connectivity first
            is_valid, stream_info = self.test_stream_connectivity(rtsp_url)
            if not is_valid:
                return False, "Invalid or unreachable RTSP stream", None
            
            # Convert to HLS (preferred for Cast)
            hls_path = os.path.join(stream_dir, "playlist.m3u8")
            success, error = self.convert_to_hls(rtsp_url, hls_path)
            
            if not success:
                # Try DASH as fallback
                dash_path = os.path.join(stream_dir, "manifest.mpd")
                success, error = self.convert_to_dash(rtsp_url, dash_path)
                if not success:
                    return False, f"Both HLS and DASH conversion failed: {error}", None
            
            # Create local HTTP server
            server_url, httpd, server_thread = self.create_local_http_server(stream_dir)
            
            if not server_url:
                return False, "Failed to create local HTTP server", None
            
            # Determine final URL
            if os.path.exists(hls_path):
                stream_url = f"{server_url}/playlist.m3u8"
                format_type = "HLS"
            else:
                stream_url = f"{server_url}/manifest.mpd"
                format_type = "DASH"
            
            # Store stream info for cleanup
            stream_info = {
                'id': stream_id,
                'device_name': device_name,
                'original_url': rtsp_url,
                'processed_url': stream_url,
                'format': format_type,
                'httpd': httpd,
                'server_thread': server_thread,
                'created_at': time.time(),
                'stream_info': stream_info
            }
            
            self.active_streams[stream_id] = stream_info
            logger.info(f"Stream processed successfully: {format_type} -> {stream_url}")
            
            return True, stream_url, stream_info
            
        except Exception as e:
            error_msg = f"Stream processing failed: {e}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def cleanup_stream(self, stream_id):
        """Clean up stream resources"""
        try:
            if stream_id in self.active_streams:
                stream_info = self.active_streams[stream_id]
                
                # Stop HTTP server
                if stream_info.get('httpd'):
                    stream_info['httpd'].shutdown()
                
                # Remove stream directory
                stream_dir = os.path.join(self.temp_dir, stream_id)
                if os.path.exists(stream_dir):
                    import shutil
                    shutil.rmtree(stream_dir)
                
                # Remove from active streams
                del self.active_streams[stream_id]
                
                logger.info(f"Cleaned up stream: {stream_id}")
                
        except Exception as e:
            logger.error(f"Stream cleanup failed: {e}")
    
    def cleanup_old_streams(self, max_age_hours=1):
        """Clean up old streams to prevent resource leaks"""
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            expired_streams = []
            for stream_id, stream_info in self.active_streams.items():
                age = current_time - stream_info['created_at']
                if age > max_age_seconds:
                    expired_streams.append(stream_id)
            
            for stream_id in expired_streams:
                self.cleanup_stream(stream_id)
                
            if expired_streams:
                logger.info(f"Cleaned up {len(expired_streams)} expired streams")
                
        except Exception as e:
            logger.error(f"Old stream cleanup failed: {e}")
    
    def get_stream_status(self, stream_id):
        """Get status of a processed stream"""
        if stream_id in self.active_streams:
            stream_info = self.active_streams[stream_id]
            return {
                'id': stream_id,
                'status': 'active',
                'format': stream_info['format'],
                'processed_url': stream_info['processed_url'],
                'device_name': stream_info.get('device_name'),
                'age_seconds': time.time() - stream_info['created_at']
            }
        return None