//sticky and unsticky
let stickyBtnAll = document.querySelectorAll('#sticky-btn');
for (let i = 0; i < stickyBtnAll.length; i++) {
    stickyBtnAll[i].addEventListener('click', function(e){
        e.preventDefault();
        postlocation = '/tweet/sticky';
        let ident = e.target.dataset.ident;
        let data = { ident: ident };

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
