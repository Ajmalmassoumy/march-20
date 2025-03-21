async function uploadVideo() {
    const videoInput = document.getElementById('videoInput');
    if (videoInput.files.length === 0) {
        alert("Please select a video file to upload.");
        return;
    }

    const formData = new FormData();
    formData.append('file', videoInput.files[0]);

    // Disable buttons to prevent multiple uploads
    document.getElementById('uploadBtn').disabled = true;
    document.getElementById('translateBtn').disabled = true;

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();
        if (response.ok) {
            alert(data.message);

            // Enable Translate button after successful upload
            document.getElementById('translateBtn').disabled = false;

            // Show the video and subtitles
            showVideoThumbnail(data.video_path); 
        } else {
            alert("Failed to upload video: " + (data.error || "Unknown error"));
        }
    } catch (error) {
        alert("An error occurred during the upload.");
        console.error(error);
    } finally {
        document.getElementById('uploadBtn').disabled = false;
    }
}

// Function to display video with subtitles
function showVideoThumbnail(videoPath) {
    const videoElement = document.getElementById('videoPlayer');
    const subtitleTrack = document.getElementById('subtitleTrack');
    const videoUrl = `/get_video?video_path=${videoPath}`;

    videoElement.src = videoUrl;
    subtitleTrack.src = `/get_subtitles?video_path=${videoPath}`; // Link to subtitle file
}

// Function to download translated subtitles
function downloadTranslatedSubtitles() {
    fetch('/download_translated_subtitles')
        .then(response => {
            if (response.ok) {
                return response.blob();
            } else {
                throw new Error('Subtitle file not found');
            }
        })
        .then(blob => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'translated_subtitles.vtt';  // Updated to correct format
            a.click();
            URL.revokeObjectURL(url);
        })
        .catch(error => {
            console.error('Error downloading subtitles:', error);
        });
}

// Function to start translation process
async function translateSubtitles() {
    const videoInput = document.getElementById('videoInput');
    if (videoInput.files.length === 0) {
        alert("Please upload a video first.");
        return;
    }

    const selectedLanguage = document.getElementById('languageSelect').value;
    const progressBar = document.getElementById('progressBar');
    progressBar.style.display = 'block';
    progressBar.value = 5; // Set initial value

    try {
        // Start checking progress in parallel
        const progressChecker = checkProgress();

        const response = await fetch('/translate', {
            method: 'POST',
            body: JSON.stringify({ 
                video_file_path: videoInput.files[0].name,  // Ensure correct filename is used
                target_language: selectedLanguage 
            }),
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) {
            throw new Error("Translation request failed.");
        }

        const data = await response.json();
        alert(data.message);

        document.getElementById('downloadBtn').disabled = false;
        document.getElementById('downloadSubtitleBtn').disabled = false;

        // Wait for progress check to complete
        await progressChecker;

    } catch (error) {
        alert("An error occurred while translating subtitles.");
        console.error(error);
    } finally {
        progressBar.style.display = 'none';
    }
}

// Function to track translation progress
async function checkProgress() {
    const progressBar = document.getElementById('progressBar');
    progressBar.style.display = 'block';

    let progress = 0;
    while (progress < 100) {
        await new Promise(resolve => setTimeout(resolve, 2000)); // Check every 2 seconds

        try {
            const response = await fetch('/progress');
            if (!response.ok) {
                throw new Error("Failed to fetch progress.");
            }

            const data = await response.json();
            progress = data.progress || 0;
            progressBar.value = progress;

            if (progress >= 100) break;

        } catch (error) {
            console.error("Error fetching progress:", error);
            break;
        }
    }

    progressBar.value = 100;
}

// Function to download the video with subtitles
async function downloadVideoWithSubtitles() {
    const response = await fetch('/download_video_with_subtitles', { method: 'GET' });

    if (response.ok) {
        const data = await response.blob();
        const url = URL.createObjectURL(data);
        const link = document.createElement('a');
        link.href = url;
        link.download = "video_with_subtitles.mp4";  // Set the default download file name
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    } else {
        alert("Error downloading video with subtitles.");
    }
}
