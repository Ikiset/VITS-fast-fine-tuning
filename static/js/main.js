document.addEventListener("DOMContentLoaded", function () {
  // button
  const uploadButton = document.getElementById("upload-field");
  const preprocessButton = document.getElementById("preprocess-field");
  const preprocessStart = document.getElementById("start-preprocess-button");
  const preprocessStop = document.getElementById("stop-preprocess-button");

  // div
  const progressDiv = document.getElementById("progress");
  const uploadView = document.getElementById("upload-view");
  const preprocessView = document.getElementById("preprocess-view");

  let progressInterval;

  fetchGetUploadedFiles();

  uploadButton.addEventListener("click", function () {
    uploadView.classList.remove("hidden");
    preprocessView.classList.add("hidden");
  });

  preprocessButton.addEventListener("click", function () {
    preprocessView.classList.remove("hidden");
    uploadView.classList.add("hidden");
  });

  preprocessStart.addEventListener("click", function () {
    preprocessStop.classList.remove("hidden");
    preprocessStart.classList.add("hidden");
    fetch("/preprocess")
      .then((response) => response.json())
      .catch((error) => {
        console.error(
          "Erreur lors de la récupération de l'avancement :",
          error
        );
      });
    progressInterval = setInterval(fetchProgress, 1000);
  });

  preprocessStop.addEventListener("click", function () {
    preprocessStart.classList.remove("hidden");
    preprocessStop.classList.add("hidden");
    fetchStopPreprocessing();
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
        console.error(
          "Erreur lors de la récupération de l'avancement :",
          error
        );
      });
  }

  function fetchStopPreprocessing() {
    fetch("/stop_processing")
      .then((response) => response.json())
      .catch((error) => {
        console.error("Erreur lors de l'arrêt du traitement :", error);
      });
  }
});

document.getElementById("refresh").addEventListener("click", function () {
  fetchGetUploadedFiles();
});

document.getElementById("remove_file").addEventListener("click", function () {
  fetchRemoveFile();
  fetchGetUploadedFiles();
});

document
  .getElementById("upload-file-button")
  .addEventListener("click", function () {
    fetchUploadFile();
    fetchGetUploadedFiles();
  });

// updateProgress();

function fetchGetUploadedFiles() {
  fetch("/get_uploaded_files")
    .then((response) => response.json())
    .then((data) => {
      const filesDiv = document.getElementById("files");
      const fileList = data.files;

      if (fileList.length === 0) {
        filesDiv.textContent = "Veuiller chargé un zip";
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
    .then((response) => response.text())
    .then(() => {
      resultDiv.textContent = "File successfully loaded";

      const newFileInput = document.createElement("input");
      newFileInput.type = "file";
      newFileInput.id = "fileInput";
      //   newFileInput.accept = ".zip";

      fileInput.parentNode.replaceChild(newFileInput, fileInput);
    })
    .catch((error) => {
      resultDiv.textContent = "Erreur lors du téléchargement du fichier";
    });
}
