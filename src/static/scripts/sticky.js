//sticky and unsticky
let stickyBtnAll = document.querySelectorAll('#sticky-btn');
for (let i = 0; i < stickyBtnAll.length; i++) {
    stickyBtnAll[i].addEventListener('click', function(e){
        e.preventDefault();
        postlocation = 'http://localhost:5000/tweet/sticky';
        let tweetid = e.target.dataset.tweetid;
        let data = { tweet_id: tweetid };

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
            if (stickyBtnAll[i].value == 'Sticky') {
                stickyBtnAll[i].value = 'Unsticky';
            } else {
                stickyBtnAll[i].value = 'Sticky';
            }
          } else {
            console.log('Error sticking post');
          }
        });
    });
}
