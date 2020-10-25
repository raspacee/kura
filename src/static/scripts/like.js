
const likeBtnAll = document.querySelectorAll('#like-btn');
for (let i = 0; i < likeBtnAll.length; i++) {
    likeBtnAll[i].addEventListener('click', function(e) {
        e.preventDefault();
        postlocation = 'http://localhost:5000/tweet/like';
        let tweetid = e.target.dataset.tweetid;
        let data = { tweet_id : tweetid };

        fetch(postlocation, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
          if (data.statuscode == 0) {
            likeCounter = likeBtnAll[i].nextElementSibling;
            likes = likeCounter.innerText;
            if (data.status == "Unliked") {
              likes = Number(likes) + 1;
              likeBtnAll[i].src = '/static/images/liked.svg';
            } else {
              likes = Number(likes) - 1;
              likeBtnAll[i].src = '/static/images/unliked.svg';
            }
            likeCounter.innerText = likes;
          } else {
            console.log('Error occured');
          }
        });
    });
}
