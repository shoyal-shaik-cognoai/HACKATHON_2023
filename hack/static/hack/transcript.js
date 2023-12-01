var loader = document.querySelector(".loader");

function startInterviews() {
  const interviewTable = document.querySelector(".overlay-table.interview");
  const otherTable = document.querySelector(".overlay-table.other");
  const startInterviewButton = document.querySelector(".start-interviews-btn");
  const hireNowButton = document.querySelector(".data-row button");
  const statusApproved = document.querySelector(".data-row .status-approved");
  const overlay = document.querySelector(".overlay-content");
  

  // Hide the current table and the button, and show the loader
  otherTable.style.display = "none";
  overlay.style.display = "none";
  startInterviewButton.style.display = "none";
  loader.style.display = "block";

  // Simulate data loading after 2 seconds
  setTimeout(() => {
    // Hide the loader
    loader.style.display = "none";

    // Simulate loading data for the other table
    // For now, let's add a dummy row after 2 seconds
    const interviewTableBody = document.querySelector(
      ".overlay-table.interview tbody"
    );
    const newRow = document.createElement("tr");
    const cell1 = document.createElement("td");
    cell1.textContent = "Loaded Candidate";
    const cell2 = document.createElement("td");
    cell2.textContent = "Loaded Transcript";
    const cell3 = document.createElement("td");
    cell3.textContent = "Loaded Result";
    newRow.appendChild(cell1);
    newRow.appendChild(cell2);
    newRow.appendChild(cell3);
    interviewTableBody.innerHTML = ""; // Clear existing data
    interviewTableBody.appendChild(newRow);

    // Show the other table
    interviewTable.style.display = "table";

    // Show the button again
    startInterviewButton.style.display = "none";
    overlay.style.display = "block";

    // Update the "Hire Now" button and status in the data table
    hireNowButton.disabled = true;
    hireNowButton.textContent = "Done";
    statusApproved.textContent = "Check Results";
  }, 2000);
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
    if(data[x].status == "pending"){
      inputButton.innerHTML = "Shortlist"
    }else{
      inputButton.innerHTML = "Open List"
    }
    inputButton.id = data[x].job_pk
    inputButton.addEventListener('click', openOverlay);
    const cell5 = document.createElement("td")
    cell5.appendChild(inputButton)
    const cell6 = document.createElement("td");
    if(data[x].status == "pending"){
      cell6.textContent = "Pending"
    }else if(data[x].status == "resume_shortlist"){
      cell6.textContent = "Resume Shortlisted"
    }else{
      cell6.textContent = "Candidates Shortlisted"
    }
    
    cell6.id = "status"
    newRow.appendChild(cell1);
    newRow.appendChild(cell2);
    newRow.appendChild(cell4);
    newRow.appendChild(cell5);
    newRow.appendChild(cell6);
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

// function shortlist_candidate(jobId) {
//   fetch(`/cv-short-list-query/?job_pk=${String(jobId)}`, {
//     method: "GET",
//     headers: {
//       "Content-Type": "application/json",
//     },
//   })
//     .then((response) => response.json())
//     .then((data) => {
//       const loader = document.querySelector(".loader");
//       loader.style.display = "none";
//       document.getElementById("overlay").style.display = "block";
//       addRows(data.selected_candidates);
//     })
//     .catch((error) => {
//       console.error("Error:", error);
//     });
// }

async function shortlist_candidate(jobId) {
  try {
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
    addRows(data.selected_candidates);
    var status = document.getElementById("status");
    status.innerHTML = "Resume Shortlisted"
  } catch (error) {
    console.error("Error:", error);
  }
}

function openOverlay() {
  if(this.innerHTML == "Shortlist"){
    shortlist_candidate(this.id)
    this.innerHTML = "Open List"
  }else{
    getCandidateData(this.id)
  }
  // document.getElementById("overlay").style.display = "block";
  // addRows();
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
