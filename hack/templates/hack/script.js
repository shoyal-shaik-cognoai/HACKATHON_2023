function startInterviews() {
    const interviewTable = document.querySelector('.overlay-table.interview');
    const otherTable = document.querySelector('.overlay-table.other');
    const startInterviewButton = document.querySelector('.start-interviews-btn');
    const loader = document.querySelector('.loader');
    const hireNowButton = document.querySelector('.data-row button');
    const statusApproved = document.querySelector('.data-row .status-approved');
    const overlay = document.querySelector('.overlay-content')

    // Hide the current table and the button, and show the loader
    otherTable.style.display = 'none';
    overlay.style.display = 'none';
    startInterviewButton.style.display = 'none';
    loader.style.display = 'block';

    // Simulate data loading after 2 seconds
    setTimeout(() => {
        // Hide the loader
        loader.style.display = 'none';

        // Simulate loading data for the other table
        // For now, let's add a dummy row after 2 seconds
        const interviewTableBody = document.querySelector('.overlay-table.interview tbody');
        const newRow = document.createElement('tr');
        const cell1 = document.createElement('td');
        cell1.textContent = 'Loaded Candidate';
        const cell2 = document.createElement('td');
        cell2.textContent = 'Loaded Transcript';
        const cell3 = document.createElement('td');
        cell3.textContent = 'Loaded Result';
        newRow.appendChild(cell1);
        newRow.appendChild(cell2);
        newRow.appendChild(cell3);
        interviewTableBody.innerHTML = ''; // Clear existing data
        interviewTableBody.appendChild(newRow);

        // Show the other table
        interviewTable.style.display = 'table';

        // Show the button again
        startInterviewButton.style.display = 'none';
        overlay.style.display = "block";

        // Update the "Hire Now" button and status in the data table
        hireNowButton.disabled = true;
        hireNowButton.textContent = 'Done';
        statusApproved.textContent = 'Check Results';
    }, 2000);
}

/*function checkData() {
    const startInterviewButton = document.querySelector('.start-interviews-btn');
    if (startInterviewButton.style.display == "none"){
        return
    }
    const otherTable = document.querySelector('.overlay-table.other');
    const interviewTableBody = document.querySelector('.overlay-table.other tbody');
    const newRow = document.createElement('tr');
    const cell1 = document.createElement('td');
    cell1.textContent = 'Loaded Candidate';
    const cell2 = document.createElement('td');
    cell2.textContent = 'Loaded Transcript';
    const cell3 = document.createElement('td');
    cell3.textContent = 'Loaded Result';
    newRow.appendChild(cell1);
    newRow.appendChild(cell2);
    newRow.appendChild(cell3);
    interviewTableBody.innerHTML = ''; // Clear existing data
    interviewTableBody.appendChild(newRow);
}*/


function openOverlay() {
    document.getElementById("overlay").style.display = "block";
}

function closeOverlay() {
    document.getElementById("overlay").style.display = "none";
}