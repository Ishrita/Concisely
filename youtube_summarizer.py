import os
import sys
import time
import yt_dlp
import whisper               
import re
import uuid
from transformers import pipeline
from tqdm import tqdm
import argparse
import warnings
warnings.filterwarnings('ignore')

class YouTubeVideoSummarizer:
    def __init__(self, output_dir="temp_files", whisper_model="tiny", max_chunk_size=900):
        """Initialize the YouTube Summarizer with configurable parameters"""
        self.output_dir = output_dir
        self.whisper_model_size = whisper_model
        self.max_chunk_size = max_chunk_size
        self.whisper_model = None
        self.summarizer = None
       
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
       
    def _load_whisper_model(self):
        """Load the Whisper model if not already loaded"""
        if self.whisper_model is None:
            print("Loading Whisper model...")
            self.whisper_model = whisper.load_model(self.whisper_model_size)
        return self.whisper_model
   
    def _load_summarizer(self):
        """Load the summarization model if not already loaded"""
        if self.summarizer is None:
            print("Loading summarization model...")
            self.summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        return self.summarizer
   
    def _extract_video_id(self, youtube_url):
        """Extract the video ID from a YouTube URL"""
        # Match patterns like: youtube.com/watch?v=VIDEO_ID or youtu.be/VIDEO_ID
        regex_patterns = [
            r"(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\?\/]+)",
            r"(?:youtube\.com\/embed\/)([^&\?\/]+)",
            r"(?:youtube\.com\/v\/)([^&\?\/]+)"
        ]
       
        for pattern in regex_patterns:
            match = re.search(pattern, youtube_url)
            if match:
                return match.group(1)
       
        # If no pattern matches, generate a unique ID based on the URL
        return str(uuid.uuid5(uuid.NAMESPACE_URL, youtube_url))
   
    def download_audio(self, youtube_url):
        """Download the audio from a YouTube video using yt-dlp"""
        try:
            # Extract video ID or create unique identifier
            video_id = self._extract_video_id(youtube_url)
           
            # Define output file path with video ID for uniqueness
            output_file = os.path.join(self.output_dir, f"audio_{video_id}.mp3")
           
            # Define yt-dlp options
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': output_file.replace('.mp3', ''),
                'quiet': False,
                'no_warnings': True,
                'force_generic_extractor': False
            }
           
            # Get video information first
            print(f"📌 Retrieving video information...")
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                title = info.get('title', 'Unknown Title')
                duration = info.get('duration', 0)
               
                # Check if video is too long
                if duration > 3600:  # longer than 1 hour
                    print(f"⚠️ Warning: This video is {round(duration/60, 2)} minutes long, processing may take a while.")
           
            print(f"🎬 Video: {title}")
            print(f"🔗 Video ID: {video_id}")
            print(f"⏱️ Length: {round(duration/60, 2)} minutes")
           
            # Download the audio (force redownload even if file exists)
            print(f"⬇️ Downloading audio to {output_file}...")
           
            # Check if file exists and remove it to force fresh download
            if os.path.exists(output_file):
                print(f"🗑️ Removing existing file to ensure fresh download")
                os.remove(output_file)
           
            start_time = time.time()
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
           
            download_time = time.time() - start_time
            print(f"✅ Audio downloaded successfully in {round(download_time, 2)} seconds")
           
            return output_file, title, duration, video_id
       
        except Exception as e:
            print(f"❌ Error downloading audio: {str(e)}")
            return None, None, None, None

    def transcribe_audio(self, audio_file):
        """Transcribe the audio file using Whisper"""
        try:
            model = self._load_whisper_model()
           
            print("🎙️ Starting transcription (this may take several minutes for long videos)...")
            start_time = time.time()
            result = model.transcribe(audio_file)
           
            transcription_time = time.time() - start_time
            print(f"✅ Transcription completed in {round(transcription_time, 2)} seconds")
           
            return result["text"]
       
        except Exception as e:
            print(f"❌ Error transcribing audio: {str(e)}")
            return None

    def chunk_text(self, text):
        """Split text into chunks of approximately max_chunk_size characters"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0
       
        for word in words:
            if current_size + len(word) + 1 > self.max_chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_size = len(word)
            else:
                current_chunk.append(word)
                current_size += len(word) + 1
               
        if current_chunk:
            chunks.append(' '.join(current_chunk))
           
        return chunks

    def summarize_text(self, text):
        """Summarize the text using a transformers model"""
        try:
            summarizer = self._load_summarizer()
           
            # Split the text into chunks
            chunks = self.chunk_text(text)
            print(f"📝 Text split into {len(chunks)} chunks for processing")
           
            summaries = []
            print("🔄 Summarizing text chunks...")
            start_time = time.time()
           
            for i, chunk in enumerate(tqdm(chunks)):
                if not chunk.strip():
                    continue
                
                max_length = min(150, int(len(chunk.split()) * 0.7))
                min_length = max(30, int(len(chunk.split()) * 0.3))
                
                summary = summarizer(chunk, max_length=max_length, min_length=min_length, do_sample=False)
                summaries.append(summary[0]['summary_text'])
           
            # Combine the summaries
            full_summary = " ".join(summaries)
           
            # If the combined summary is still long, summarize it again
            if len(full_summary) > 2000:
                print("🔄 Generating final summary from intermediate summaries...")
                chunks = self.chunk_text(full_summary)
                second_summaries = []
                for chunk in tqdm(chunks):
                    if not chunk.strip():
                        continue
                    summary = summarizer(chunk, max_length=150, min_length=30, do_sample=False)
                    second_summaries.append(summary[0]['summary_text'])
                full_summary = " ".join(second_summaries)
           
            summarization_time = time.time() - start_time
            print(f"✅ Summarization completed in {round(summarization_time, 2)} seconds")
               
            return full_summary
       
        except Exception as e:
            print(f"❌ Error summarizing text: {str(e)}")
            return None

    def process_video(self, youtube_url, save_files=True, cleanup=True):
        """Main function to summarize a YouTube video"""
        print(f"🚀 Starting to process video: {youtube_url}")
        start_time = time.time()
       
        # Step 1: Download the audio using yt-dlp
        audio_file, title, duration, video_id = self.download_audio(youtube_url)
        if not audio_file:
            return "Failed to download audio from the video."
       
        try:
            # Step 2: Transcribe the audio
            transcription = self.transcribe_audio(audio_file)
            if not transcription:
                return "Failed to transcribe the audio."
           
            # Step 3: Summarize the transcript
            summary = self.summarize_text(transcription)
            if not summary:
                return "Failed to summarize the transcript."
           
            # Step 4: Clean up if requested
            if cleanup:
                try:
                    os.remove(audio_file)
                    print(f"🧹 Temporary audio file removed")
                except:
                    print("Note: Could not remove temporary file")
           
            # Save to files if requested
            if save_files:
                # Create safe filename based on video ID and title
                safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
                safe_title = re.sub(r'[-\s]+', '-', safe_title)
                safe_title = safe_title[:50]  # Limit length
               
                output_base = os.path.join(self.output_dir, f"{video_id}_{safe_title}")
               
                transcript_file = f"{output_base}_transcript.txt"
                summary_file = f"{output_base}_summary.txt"
               
                with open(transcript_file, "w", encoding="utf-8") as f:
                    f.write(transcription)
               
                with open(summary_file, "w", encoding="utf-8") as f:
                    f.write(summary)
               
                print(f"📄 Files saved to:\n - {transcript_file}\n - {summary_file}")
           
            total_time = time.time() - start_time
            compression_ratio = round(len(summary)/len(transcription)*100, 1)
           
            print("\n===== VIDEO SUMMARY =====")
            print(f"🎬 Title: {title}")
            print(f"🔗 URL: {youtube_url}")
            print(f"🆔 Video ID: {video_id}")
            print(f"⏱️ Video Length: {round(duration/60, 2)} minutes")
            print(f"📊 Transcription Length: {len(transcription)} characters")
            print(f"📊 Summary Length: {len(summary)} characters ({compression_ratio}% of original)")
            print(f"⏱️ Total Processing Time: {round(total_time, 2)} seconds")
           
            # Display results
            print("\n=== SUMMARY ===")
            print(summary)
           
            return {
                "title": title,
                "youtube_url": youtube_url,
                "video_id": video_id,
                "duration": duration,
                "transcription": transcription,
                "summary": summary,
                "processing_time": total_time,
                "compression_ratio": compression_ratio
            }
       
        except Exception as e:
            # If the temporary file exists, remove it
            try:
                if audio_file and os.path.exists(audio_file):
                    os.remove(audio_file)
            except:
                pass
           
            print(f"❌ Error processing video: {str(e)}")
            return f"Error processing video: {str(e)}"


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='YouTube Video Summarizer')
    parser.add_argument('--url', type=str, help='YouTube video URL')
    parser.add_argument('--model', type=str, default='tiny',
                        choices=['tiny', 'base', 'small', 'medium', 'large'],
                        help='Whisper model size (default: tiny)')
    parser.add_argument('--output', type=str, default='temp_files',
                        help='Output directory for files (default: temp_files)')
    parser.add_argument('--no-save', action='store_false', dest='save_files',
                        help='Do not save transcript and summary files')
    parser.add_argument('--no-cleanup', action='store_false', dest='cleanup',
                        help='Do not delete temporary audio files')
    return parser.parse_args()


# Run the code if executed directly
if __name__ == "__main__":
    # Check if running in Jupyter or as a script
    is_jupyter = 'ipykernel' in sys.modules
   
    if is_jupyter:
        # For Jupyter notebook usage
        # Create the summarizer with default settings
        summarizer = YouTubeVideoSummarizer(whisper_model="tiny")
       
        # Example usage:
        # Uncomment the line below and replace with your YouTube video URL
        results = summarizer.process_video("https://youtu.be/tl_6rcm0zPk")
    else:
        # For command-line usage
        args = parse_arguments()
        if args.url:
            summarizer = YouTubeVideoSummarizer(
                output_dir=args.output,
                whisper_model=args.model
            )
            summarizer.process_video(
                args.url,
                save_files=args.save_files,
                cleanup=args.cleanup
            )
        else:
            print("Please provide a YouTube URL with the --url argument")