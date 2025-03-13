from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse
import subprocess
import requests
from typing import AsyncGenerator
import asyncio
import logging
import json
from urllib.parse import urlparse
import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

async def stream_video(url: str) -> AsyncGenerator[bytes, None]:
    """Stream video with AAC audio transcoding on-the-fly."""
    try:
        logger.info(f"Starting video transcoding for URL: {url}")
        
        # FFmpeg command to transcode audio to AAC while copying video stream
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', 'pipe:0',          # Input from pipe
            '-c:v', 'copy',          # Copy video stream (no re-encoding)
            '-c:a', 'aac',           # Transcode audio to AAC
            '-b:a', '128k',          # Audio bitrate
            '-ac', '2',              # Force 2 audio channels (stereo)
            '-ar', '44100',          # Set audio sample rate to 44.1kHz (iOS compatible)
            '-f', 'mp4',             # Output format
            '-movflags', 'frag_keyframe+empty_moov+default_base_moof',  # Enable streaming
            'pipe:1'                 # Output to pipe
        ]
        
        logger.info(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")

        # Start FFmpeg process
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        logger.info("FFmpeg process started")

        # Start a task to read and log FFmpeg's stderr
        async def log_ffmpeg_output():
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                stderr_line = line.decode('utf-8', errors='replace').strip()
                if stderr_line:
                    logger.debug(f"FFmpeg: {stderr_line}")
        
        # Start the stderr reading task
        asyncio.create_task(log_ffmpeg_output())

        # Start downloading the video
        async with requests.Session() as session:
            try:
                async with session.get(url, stream=True) as response:
                    logger.info(f"Source video request status: {response.status_code}")
                    
                    if response.status_code >= 400:
                        logger.error(f"Failed to fetch source video: HTTP {response.status_code}")
                        raise Exception(f"Failed to fetch source video: HTTP {response.status_code}")
                    
                    # Stream chunks through FFmpeg
                    chunk_size = 64 * 1024  # 64KB chunks
                    chunks_processed = 0
                    async for chunk in response.iter_content(chunk_size=chunk_size):
                        if not chunk:
                            break
                        # Write chunk to FFmpeg's stdin
                        process.stdin.write(chunk)
                        # Read processed chunk from FFmpeg's stdout
                        processed_chunk = await process.stdout.read(chunk_size)
                        if processed_chunk:
                            chunks_processed += 1
                            if chunks_processed % 100 == 0:  # Log every 100 chunks
                                logger.info(f"Processed {chunks_processed} chunks ({chunks_processed * chunk_size / 1024 / 1024:.2f} MB)")
                            yield processed_chunk
            except Exception as e:
                logger.error(f"Error downloading source video: {str(e)}", exc_info=True)
                raise

        # Clean up
        if process.stdin:
            process.stdin.close()
        await process.wait()
        logger.info("Transcoding completed successfully")

    except Exception as e:
        logger.error(f"Error streaming video: {str(e)}", exc_info=True)
        raise

@router.get("/transcode")
async def transcode_video(request: Request, url: str, force: bool = False):
    """Endpoint to transcode video audio to AAC format on-the-fly."""
    try:
        # Get detailed request information
        user_agent = request.headers.get("user-agent", "")
        
        # More comprehensive iOS detection
        ios_indicators = {
            "iphone": "iphone" in user_agent.lower(),
            "ipad": "ipad" in user_agent.lower(),
            "ipod": "ipod" in user_agent.lower(),
            "ios": "ios" in user_agent.lower(),
            "mac_mobile": (("macintosh" in user_agent.lower() or "macintel" in user_agent.lower()) and 
                          "safari" in user_agent.lower() and "mobile" in user_agent.lower()),
            "safari": "safari" in user_agent.lower() and "chrome" not in user_agent.lower()
        }
        
        # Consider a device as iOS if any of the standard indicators are present
        is_ios = any([
            ios_indicators["iphone"], 
            ios_indicators["ipad"], 
            ios_indicators["ipod"],
            # Mac with Safari can be iOS-like for audio support
            (ios_indicators["mac_mobile"] and ios_indicators["safari"])
        ])
        
        # If force parameter is true, override the iOS detection
        if force:
            is_ios = True
            logger.info("iOS detection overridden by force parameter")
        
        # Enhanced logging with full details
        logger.info(json.dumps({
            "event": "transcode_request",
            "url": url,
            "user_agent": user_agent,
            "is_ios": is_ios,
            "force_transcode": force,
            "ios_indicators": ios_indicators,
            "headers": dict(request.headers),
            "client": request.client.host if request.client else None,
            "timestamp": str(datetime.datetime.now())
        }, indent=2))

        # For non-iOS devices, simply redirect to the original URL
        if not is_ios:
            logger.info("Non-iOS device detected, redirecting to original URL")
            return Response(status_code=307, headers={"Location": url})
        
        # Log that we detected an iOS device and will transcode
        logger.info("iOS device detected! Starting transcoding process")

        # Validate URL before processing
        try:
            parsed_url = urlparse(url)
            if not all([parsed_url.scheme, parsed_url.netloc]):
                logger.error(f"Invalid URL format: {url}")
                return Response(
                    status_code=400, 
                    content=json.dumps({"error": "Invalid URL format"}),
                    media_type="application/json"
                )
        except Exception as e:
            logger.error(f"URL parsing error: {str(e)}")
            return Response(
                status_code=400, 
                content=json.dumps({"error": f"Invalid URL: {str(e)}"}),
                media_type="application/json"
            )

        logger.info("iOS device detected, starting transcoding")
        
        # For iOS, stream with transcoded audio
        try:
            response = StreamingResponse(
                stream_video(url),
                media_type="video/mp4",
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Type": "video/mp4",
                    "Cache-Control": "no-cache",
                    "Access-Control-Allow-Origin": "*",  # Allow CORS
                }
            )
            
            logger.info("Streaming response initialized")
            return response
        except Exception as stream_error:
            logger.error(f"Streaming error: {str(stream_error)}", exc_info=True)
            # If streaming initialization fails, fall back to original URL
            return Response(
                status_code=307, 
                headers={"Location": url},
                content=json.dumps({"error": "Transcoding failed, redirecting to original URL"}),
                media_type="application/json"
            )

    except Exception as e:
        logger.error(f"Error in transcode endpoint: {str(e)}", exc_info=True)
        # If transcoding fails, fall back to original URL
        return Response(
            status_code=307, 
            headers={"Location": url},
            content=json.dumps({"error": str(e)}),
            media_type="application/json"
        ) 