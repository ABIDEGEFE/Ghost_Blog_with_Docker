document.addEventListener("DOMContentLoaded", function () {

    const audio = document.getElementById("audioPlayer");
    const content = document.getElementById("post-content");

    if (!audio || !content) return;

    const sentences = content.innerText.split(". ");

    let spans = [];
    content.innerHTML = "";

    sentences.forEach((sentence, index) => {
        const span = document.createElement("span");
        span.textContent = sentence + ". ";
        span.className = "sentence";
        content.appendChild(span);
        spans.push(span);
    });

    audio.addEventListener("timeupdate", function () {

        const progress = audio.currentTime / audio.duration;
        const index = Math.floor(progress * spans.length);
       
        console.log(`Audio progress: ${(progress * 100).toFixed(2)}% - Current sentence index: ${index}`);  
        spans.forEach(s => s.classList.remove("highlight"));

        if (spans[index]) {
            spans[index].classList.add("highlight");
            console.log(`Highlighting sentence ${index + 1}: ${spans[index].textContent}`);
        }

    });

});