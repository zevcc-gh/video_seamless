window.onload = function () {
    var videoElement = document.getElementById("video");
    var preloadElement = document.createElement("video");
    var idleVideoLink;

    document.getElementById("connectWS").addEventListener("click", function () {
        var canvas = document.getElementById("canvas");
        var context = canvas.getContext('2d');

        var playbackQueue = [];
        var socket = new WebSocket("ws://localhost:8000/ws/123");

        function drawFrame() {
            if (!videoElement.paused && !videoElement.ended) {
                context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
                requestAnimationFrame(drawFrame);
            }
        }

        videoElement.onplay = function () {
            drawFrame();
        }

        videoElement.oncanplaythrough = function () {
            videoElement.play();
        }

        videoElement.ontimeupdate = function () {
            if (videoElement.duration - videoElement.currentTime <= 0.1) {
                if (playbackQueue.length > 0) {
                    preloadNextVideo();
                    switchVideos();
                } else {
                    playbackQueue.push(idleVideoLink);
                    preloadNextVideo();
                    switchVideos();
                }
            }
        };

        videoElement.onerror = function () {
            console.error("Failed to play the video: " + videoElement.src);
            playbackQueue.push(idleVideoLink);
            preloadNextVideo();
            switchVideos();
        };

        socket.onmessage = function (event) {
            var data = JSON.parse(event.data);
            var videoLink = data.video_link;
            playbackQueue.push(videoLink);

            if (videoElement.paused || videoElement.src === idleVideoLink) {
                preloadNextVideo();
                switchVideos();
            }
        };

        socket.onclose = function (event) {
            console.log("WebSocket connection closed.");
        };

        function preloadNextVideo() {
            var nextVideoLink = playbackQueue.shift();
            preloadElement.src = nextVideoLink;
        }

        function switchVideos() {
            var temp = videoElement.src;
            videoElement.src = preloadElement.src;
            preloadElement.src = temp;
            videoElement.play();
        }

        function fetchIdleVideo() {
            fetch("http://localhost:8000/idle", { credentials: "include" })
                .then(function (response) {
                    return response.json();
                })
                .then(function (data) {
                    idleVideoLink = data.video_link;
                    playbackQueue.push(idleVideoLink);
                    preloadNextVideo();
                    switchVideos();
                })
                .catch(function (error) {
                    console.log("Error fetching idle video:", error);
                });
        }

        fetchIdleVideo();
    });

    document.getElementById("pause").addEventListener("click", function () {
        if (videoElement) videoElement.pause();
    });

    document.getElementById("resume").addEventListener("click", function () {
        if (videoElement) videoElement.play();
    });
}