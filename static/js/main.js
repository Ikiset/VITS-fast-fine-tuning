document.addEventListener("DOMContentLoaded", function () {
  fetchGetUploadedFiles();
});

// button
const uploadFieldButton = document.getElementById("upload-field");
const preprocessFieldButton = document.getElementById("preprocess-field");
const preprocessStart = document.getElementById("start-preprocess-button");
const preprocessStop = document.getElementById("stop-preprocess-button");
const trainStart = document.getElementById("start-train-button");
const trainStop = document.getElementById("stop-train-button");
const refresh = document.getElementById("refresh");
const removeFileButton = document.getElementById("remove_file");
const uploadFileButton = document.getElementById("upload-file-button");

// div
const progressDiv = document.getElementById("progress");
const trainProgressDiv = document.getElementById("train-progress");
const uploadView = document.getElementById("upload-view");
const preprocessView = document.getElementById("preprocess-view");

// repeat interval
let progressInterval;
let trainProgressInterval;

uploadFieldButton.addEventListener("click", function () {
  uploadView.classList.remove("hidden");
  preprocessView.classList.add("hidden");
});

preprocessFieldButton.addEventListener("click", function () {
  preprocessView.classList.remove("hidden");
  uploadView.classList.add("hidden");
});

preprocessStart.addEventListener("click", function () {
  preprocessStop.classList.remove("hidden");
  preprocessStart.classList.add("hidden");
  fetch("/preprocess")
    .then((response) => response.json())
    .catch((error) => {
      console.error("Erreur lors de la récupération de l'avancement :", error);
    });
  setTimeout(function () {
    progressInterval = setInterval(fetchProgress, 1000);
  }, 1000);
});

preprocessStop.addEventListener("click", function () {
  preprocessStart.classList.remove("hidden");
  preprocessStop.classList.add("hidden");
  fetchStopPreprocessing();
  clearInterval(progressInterval);
});

trainStart.addEventListener("click", function () {
  trainStop.classList.remove("hidden");
  trainStart.classList.add("hidden");
  fetch("/train/run").catch((error) => {
    console.error("Erreur lors de l'entrainement : ", error);
  });
  setTimeout(function () {
    trainProgressInterval = setInterval(fetchTrainProgress, 1000);
  }, 1000);
});

trainStop.addEventListener("click", function () {
  trainStart.classList.remove("hidden");
  trainStop.classList.add("hidden");
  fetchStopTrain();
  clearInterval(trainProgressInterval);
});

refresh.addEventListener("click", function () {
  fetchGetUploadedFiles();
});

removeFileButton.addEventListener("click", function () {
  fetchRemoveFile();
  setTimeout(function () {
    fetchGetUploadedFiles();
  }, 1000);
});

uploadFileButton.addEventListener("click", function () {
  fetchUploadFile();
  setTimeout(function () {
    fetchGetUploadedFiles();
  }, 1500);
});

function fetchProgress() {
  fetch("/get_progress")
    .then((response) => response.json())
    .then((data) => {
      const progress = data.progress;

      if (progress === "ended") {
        preprocessStart.classList.remove("hidden");
        preprocessStop.classList.add("hidden");

        progressDiv.textContent = "Traitement terminé";
        clearInterval(progressInterval);
      } else if (progress === "stopped") {
        progressDiv.textContent =
          progressDiv.textContent + "\t preprocess are stopped";
        clearInterval(progressInterval);
      } else {
        progressDiv.textContent = `Avancement : ${progress}`;
      }
    })
    .catch((error) => {
      console.error("Erreur lors de la récupération de l'avancement :", error);
    });
}

function fetchStopPreprocessing() {
  fetch("/stop_processing")
    .then((response) => response.json())
    .catch((error) => {
      console.error("Erreur lors de l'arrêt du traitement :", error);
    });
}

function fetchTrainProgress() {
  fetch("/train/start")
    .then((response) => response.json())
    .then((data) => {
      const epoch = data.epoch;
      const status = data.status;
      const max_epoch = data.max_epochs;
      if (status === "ended") {
        trainStart.classList.remove("hidden");
        trainStop.classList.add("hidden");
        trainProgressDiv.textContent = `Entrainement terminer : ${epoch} epoch(s)`;
        clearInterval(trainProgressInterval);
      } else {
        trainProgressDiv.textContent = `Avancement : ${epoch}/${max_epoch}`;
      }
    });
}

function fetchStopTrain() {
  fetch("/train/stop")
    .then((response) => response.json())
    .then((data) => {
      const epoch = data.epoch;
      const status = data.status;
      trainProgressDiv.textContent = `Entrainement terminer : ${status}\t${epoch} epoch(s)`;
    });
}

function fetchGetUploadedFiles() {
  fetch("/get_uploaded_files")
    .then((response) => response.json())
    .then((data) => {
      const filesDiv = document.getElementById("files");
      const fileList = data.files;

      if (fileList.length === 0) {
        filesDiv.innerHTML = "Veuillez chargé un zip<br><br>";
      } else {
        const filesListHTML = fileList
          .map((fileName) => `<p>${fileName}</p>`)
          .join("");
        filesDiv.innerHTML = `<h2>Fichiers chargés :</h2>${filesListHTML}`;
      }
    })
    .catch((error) => {
      console.error("Erreur lors de la récupération des fichiers :", error);
    });
}

function fetchRemoveFile() {
  fetch("/remove_all")
    .then((response) => response.json())
    .then(
      () =>
        (document.getElementById("files").innerHTML =
          "Tout les fichiers sont supprimés<br><br>")
    )
    .catch((error) => {
      console.error("Erreur lors des suppressions des fichiers :", error);
    });
}

function fetchUploadFile() {
  const fileInput = document.getElementById("fileInput");
  const resultDiv = document.getElementById("result");
  const file = fileInput.files[0];
  if (!file) {
    resultDiv.textContent = "Fichier non sélectionné";
    return;
  }
  const formData = new FormData();
  formData.append("file", file);

  fetch("/uploader", {
    method: "POST",
    body: formData,
  })
    .then((response) => response.json())
    .then((data) => {
      resultDiv.textContent = data.message;

      const newFileInput = document.createElement("input");
      newFileInput.type = "file";
      newFileInput.id = "fileInput";
      //   newFileInput.accept = ".zip";

      fileInput.parentNode.replaceChild(newFileInput, fileInput);
    })
    .catch((error) => {
      resultDiv.textContent = "Erreur lors du téléchargement du fichier";
      console.log(error);
    });
}
