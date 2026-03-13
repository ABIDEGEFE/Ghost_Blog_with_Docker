const audio = document.getElementById("audioPlayer");

function setSpeed(rate) {
    if(audio){
        audio.playbackRate = rate;
    }
}
