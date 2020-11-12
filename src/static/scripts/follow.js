
const followBtnAll = document.querySelectorAll('#follow-btn');
for (let i = 0; i < followBtnAll.length; i++) {
    followBtnAll[i].addEventListener('click', function(e) {
        e.preventDefault();
        postlocation = '/user/follow';
        let userid = e.target.dataset.userid;
        let data = { user_id : userid };

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
            if (followBtnAll[i].value == 'Follow') {
                followBtnAll[i].value = 'Unfollow';
            } else {
                followBtnAll[i].value = 'Follow';
            }
          } else {
            console.log('Error occured');
          }
        });
    });
}
