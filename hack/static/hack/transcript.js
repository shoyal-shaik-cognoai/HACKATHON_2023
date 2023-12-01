function startInterviews() {
  const interviewTable = document.querySelector(".overlay-table.interview");
  const otherTable = document.querySelector(".overlay-table.other");
  const startInterviewButton = document.querySelector(".start-interviews-btn");
  const loader = document.querySelector(".loader");
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
    cell3.textContent = "75%";
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
    cell1.className = "jobClass"
    cell1.addEventListener('click', getJobDesc)
    const cell2 = document.createElement("td");
    cell2.textContent = "5";
    const cell3 = document.createElement("td");
    var inputElement = document.createElement('input');
    inputElement.type = 'number';
    inputElement.placeholder = 'Enter Relevance...';
    cell3.appendChild(inputElement);
    const cell4 = document.createElement("td");
    cell4.textContent = '15'
    var inputButton = document.createElement("button");
    inputButton.innerHTML = "Hire Now"
    inputButton.id = data[x].job_title
    inputButton.addEventListener('click', openOverlay);
    const cell5 = document.createElement("td")
    cell5.appendChild(inputButton)
    const cell6 = document.createElement("td");
    cell6.textContent = "pending"
    cell6.id = "status"
    newRow.appendChild(cell1);
    newRow.appendChild(cell2);
    newRow.appendChild(cell3);
    newRow.appendChild(cell4);
    newRow.appendChild(cell5);
    newRow.appendChild(cell6);
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
function getCandidateData() {
  fetch("/get-candidate-data/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => response.json())
    .then((data) => {
      console.log(data);
      addRows(data.data);
    })
    .catch((error) => {
      console.error("Error:", error);
    });
}

getCandidateData();

function openOverlay() {
  document.getElementById("overlay").style.display = "block";
  addRows();
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
