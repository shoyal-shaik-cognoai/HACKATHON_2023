var loader = document.querySelector(".loader");

function makeRows(data){
  const interviewTable = document.querySelector(".overlay-table.interview");
  const otherTable = document.querySelector(".overlay-table.other");
  const startInterviewButton = document.querySelector(".start-interviews-btn");
  const hireNowButton = document.querySelector(".clickable-cell");
  const overlay = document.querySelector(".overlay-content");
  otherTable.style.display = "none";
  overlay.style.display = "none";
  startInterviewButton.style.display = "none";
    const interviewTableBody = document.querySelector(
      ".overlay-table.interview tbody"
    );
    for(let x in data){
      const newRow = document.createElement("tr");
      const cell1 = document.createElement("td");
      cell1.textContent = data[x][0]
      var resumeLink = document.createElement("a");
      resumeLink.href = 'http://localhost:8000/transcript-generator/?profile_pk=' + data[x][1]; // Set a placeholder href value, it will be updated later
      resumeLink.textContent = "Open Transcript";
      const cell2 = document.createElement("td");
      cell2.append(resumeLink);
  
      // resumeLink.addEventListener('click', function(event) {
      //     event.preventDefault();
      //     var newWindow = window.open('', '_blank');
      //     newWindow.document.write('<html><head><title>Transcript</title></head><body>' + data[x][1] + '</body></html>');
      //     resumeLink.href = newWindow.document.URL;
      // });
      const cell3 = document.createElement("td");
      cell3.textContent = data[x][2]
      newRow.appendChild(cell1);
      newRow.appendChild(cell2);
      newRow.appendChild(cell3);
      interviewTableBody.innerHTML = ""; // Clear existing data
      interviewTableBody.appendChild(newRow);
    }
  interviewTable.style.display = "table";

  // Show the button again
  startInterviewButton.style.display = "none";
  overlay.style.display = "block";

  // Update the "Hire Now" button and status in the data table
  hireNowButton.innerHTML = "Show Results";
  document.getElementById("overlay").style.display = "block";
}

function getScreenedCandidates(job_id){
    json_string = {
      'job_id': job_id
    }

    const xhttp = new XMLHttpRequest();
  xhttp.open("POST", '/voice-screening-result/', true); // Set the third parameter to true for asynchronous
  xhttp.setRequestHeader("Content-Type", "application/json");
  xhttp.onreadystatechange = function () {
    if (this.readyState === 4) {
      if (this.status === 200) {
        const response = JSON.parse(this.responseText);
        if (response.status === 200) {
          makeRows(response.ans_list);
        } else {
          console.error('Error in response:', response.message);
        }
      } else {
        console.error('HTTP request failed with status:', this.status);
      }
    }
  };
  xhttp.send(JSON.stringify(json_string));
}



function startInterviews() {
  loader.style.display = "block";
  setTimeout(() => {
    loader.style.display = "none";
  }, 2000);
  const json_string = {
    'job_profile_pk': window.job_id
  };
  const xhttp = new XMLHttpRequest();
  xhttp.open("POST", '/initate-call-campaign/', true); // Set the third parameter to true for asynchronous
  xhttp.setRequestHeader("Content-Type", "application/json");
  xhttp.onreadystatechange = function () {
    if (this.readyState === 4) {
      if (this.status === 200) {
        const response = JSON.parse(this.responseText);
        if (response.status === 200) {
          console.log(response.data);
        } else {
          console.error('Error in response:', response.message);
        }
      } else {
        console.error('HTTP request failed with status:', this.status);
      }
      const modalDiv = document.getElementById('overlay');
      modalDiv.style.display = 'none';
    }
  };
  xhttp.send(JSON.stringify(json_string));
  let buttons =  document.querySelectorAll(".clickable-cell")

  for (let i=0;i<buttons.length;i++){
    if (buttons[i].id == window.job_id){
      buttons[i].innerHTML = "Screen Data"
    }
  }
  // for (let x in buttons){
  //   if(x.id == window.job_id){
  //     x.innerHTML = "Screen Data"
  //   }
  // }
  // Hide the current table and the button, and show the loader
}

function addRows(data) {
  const otherTableBody = document.querySelector(".overlay-table.other tbody");
  otherTableBody.innerHTML = ""
  for (let x in data) {
    const newRow = document.createElement("tr");
    const cell1 = document.createElement("td");
    cell1.textContent = data[x].name;
    var resumeLink = document.createElement("a");
    resumeLink.href = data[x].cv_file_path;
    resumeLink.target = "_blank";
    resumeLink.textContent = "Open Resume";
    const cell2 = document.createElement("td");
    cell2.appendChild(resumeLink);
    const cell3 = document.createElement("td");
    cell3.textContent = data[x].confidence;
    newRow.appendChild(cell1);
    newRow.appendChild(cell2);
    newRow.appendChild(cell3);
    otherTableBody.appendChild(newRow);
  }
}

function addJobDesc(data){
    var modalBody = document.querySelector("#modalBody");
    modalBody.innerHTML = ""
    const title = document.createElement("h3");
    title.innerHTML = data.job_title
    const desc = document.createElement("p");
    let jobDescription = data.job_description;
    jobDescription = jobDescription.replaceAll('\n', '<br>');
    desc.innerHTML = jobDescription
    modalBody.append(title)
    modalBody.append(desc)
  

  const modalDiv = document.getElementById('myModal');
  modalDiv.style.display = 'block';
}

function getJobDesc() {
  const jobId = this.id;
  window.job_id = jobId
  const json_string = {
    'job_pk': jobId
  };

  const xhttp = new XMLHttpRequest();
  xhttp.open("POST", '/get-job-data/', true); // Set the third parameter to true for asynchronous
  xhttp.setRequestHeader("Content-Type", "application/json");
  xhttp.onreadystatechange = function () {
    if (this.readyState === 4) {
      if (this.status === 200) {
        const response = JSON.parse(this.responseText);
        if (response.status === 200) {
          console.log(response.data);
          addJobDesc(response.data);
        } else {
          console.error('Error in response:', response.message);
        }
      } else {
        console.error('HTTP request failed with status:', this.status);
      }
    }
  };
  xhttp.send(JSON.stringify(json_string));
}

function addJobRoles(data) {
  const dataTableBody = document.querySelector(".data-table tbody");
  for (let x in data) {
    const newRow = document.createElement("tr");
    const cell1 = document.createElement("td");
    cell1.textContent = data[x].job_title;
    cell1.id = data[x].job_pk
    cell1.className = "title"
    cell1.addEventListener('click', getJobDesc)
    const cell2 = document.createElement("td");
    cell2.textContent = "5";
    const cell4 = document.createElement("td");
    cell4.textContent = '15'
    var inputButton = document.createElement("button");
    console.log(data[x].status)
    if(data[x].status == "pending"){
      inputButton.innerHTML = "Shortlist"
    }else if(data[x].status == "resume_shortlist"){
      inputButton.innerHTML = "Open List"
    }
    inputButton.id = data[x].job_pk
    inputButton.className = "clickable-cell"
    inputButton.addEventListener("click", openOverlay)
    const cell5 = document.createElement("td")
    cell5.appendChild(inputButton)
    newRow.appendChild(cell1);
    newRow.appendChild(cell2);
    newRow.appendChild(cell4);
    newRow.appendChild(cell5);
    newRow.className = "data-table"
    dataTableBody.appendChild(newRow);
  }
}

function getJobRoles() {
  fetch("/get-job-data/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => response.json())
    .then((data) => {
      console.log(data);
      addJobRoles(data.data);
    })
    .catch((error) => {
      console.error("Error:", error);
    });
}
getJobRoles();
function getCandidateData(job_id) {
  window.job_id = job_id;
  fetch("/get-candidate-data/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({job_id}),
  })
    .then((response) => response.json())
    .then((data) => {
      console.log(data);
      document.getElementById("overlay").style.display = "block";
      addRows(data.data);
    })
    .catch((error) => {
      console.error("Error:", error);
    });
}

async function shortlist_candidate(jobId) {
  try {
    window.job_id = jobId
    const loader = document.querySelector(".loader");
    const bodyElement = document.querySelector('body');
    loader.style.display = "block";
    bodyElement.style.backgroundColor = 'rgba(255, 255, 255, 0.7)';
    bodyElement.style.zIndex = 9999

    const response = await fetch(`/cv-short-list-query/?job_pk=${String(jobId)}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP request failed with status: ${response.status}`);
    }

    const data = await response.json();

    loader.style.display = "none";
    document.getElementById("overlay").style.display = "block";
    addRows(data.selected_candidates)
  } catch (error) {
    console.error("Error:", error);
  }
}

function openOverlay() {
  console.log(this.id)
  if(this.innerHTML == "Shortlist"){
    this.innerHTML = "Open List"
    shortlist_candidate(this.id)
  }else if(this.innerHTML == "Open List"){
    getCandidateData(this.id)
    window.job_id = this.id
  }else if(this.innerHTML == "Screen Data"){
    getScreenedCandidates(this.id)
    window.job_id = this.id
  }else if(this.innerHTML == "Show Results"){
    document.getElementById("overlay").style.display = "block";
  }
}

function closeOverlay() {
  document.getElementById("overlay").style.display = "none";
}

// Get the modal and the job cell
var modal = document.getElementById("myModal");
var jobCell = document.getElementById("jobCell");

// Get the close button inside the modal
var closeBtn = document.getElementsByClassName("close")[0];

// Show the modal when clicking on the job cell
// jobCell.addEventListener("click", function () {
//   modal.style.display = "block";
// });

// Close the modal when clicking on the close button
closeBtn.addEventListener("click", function () {
  modal.style.display = "none";
});

// Close the modal when clicking outside of it
window.addEventListener("click", function (event) {
  if (event.target == modal) {
    modal.style.display = "none";
  }
});