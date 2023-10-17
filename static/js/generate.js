document.addEventListener("DOMContentLoaded", function () {
  fillModelDropdown();
});

const addModelButton = document.getElementById("add-model-button");
const uploadModelViewCloseButton = document.getElementById(
  "upload-model-view-close"
);
const uploadModelForm = document.getElementById("upload-model-form");
const buttonGenerateText = document.getElementById("send-text-to-generate");
const downloadAudio = document.getElementById("download-audio-file");

addModelButton.addEventListener("click", () => {
  const uploadModelView = document.getElementById("upload-model-view");
  uploadModelView.classList.remove("hidden");
});

uploadModelViewCloseButton.addEventListener("click", () => {
  const uploadModelView = document.getElementById("upload-model-view");
  uploadModelView.classList.add("hidden");
});

uploadModelForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const formData = new FormData(uploadModelForm);
  const uploadResult = document.getElementById("upload-result");

  fetch("/upload_model", {
    method: "POST",
    body: formData,
  })
    .then((response) => response.json())
    .then((data) => {
      uploadResult.textContent = data.message;
      fillModelDropdown();
      setTimeout(function () {
        uploadResult.textContent = "";
      }, 10000);
    })
    .catch((error) => {
      uploadResult.textContent = "Erreur lors de l'envoi du modèle.";
    });
});

function fillModelDropdown() {
  const modelSelect = document.getElementById("model-select");

  fetch("/get_models")
    .then((response) => response.json())
    .then((data) => {
      modelSelect.innerHTML = "";
      data.models.forEach((model) => {
        const option = document.createElement("option");
        option.value = model;
        option.textContent = model;
        modelSelect.appendChild(option);
      });
    })
    .catch((error) => {
      console.error("Erreur lors du chargement des modèles :", error);
    });
}

document.getElementById("select-model-button").addEventListener("click", () => {
  const modelSelect = document.getElementById("model-select");
  const selectedModel = modelSelect.value;

  fetch("/generate/model", {
    method: "POST",
    body: JSON.stringify({ model_name: selectedModel }),
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => response.json())
    .then((data) => alert(data.message))
    .catch((error) => "Error in selection of model : " + error);
});

document.getElementById("delete-model-button").addEventListener("click", () => {
  const model_name =
    document.getElementById("model-select").selectedOptions[0].textContent;
  const deleteResult = document.getElementById("delete-result");

  fetch("/delete_model", {
    method: "POST",
    body: JSON.stringify({ model_name: model_name }),
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => response.json())
    .then((data) => {
      deleteResult.textContent = data.message;
      fillModelDropdown();
      setTimeout(function () {
        deleteResultResult.textContent = "";
      }, 10000);
    })
    .catch((error) => {
      console.error("Erreur lors du chargement des modèles :", error);
    });
});

buttonGenerateText.addEventListener("click", () => {
  const generateText = document.getElementById("text-to-generate");
  const generateResult = document.getElementById("generateResult");
  const speakerID = document.getElementById("speaker-select");
  const audioFile = document.getElementById("audio-file");
  const downloadAudioFile = document.getElementById("download-audio-file");
  fetch("/generate_text", {
    method: "POST",
    body: JSON.stringify({
      text: generateText.value,
      speaker: speakerID.value,
    }),
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => response.json())
    .then((data) => {
      generateResult.textContent = data.message;
      audioFile.innerHTML = '<audio controls src="/generate/wav"></audio>';
      downloadAudioFile.classList.remove("hidden");
      setTimeout(function () {
        generateResult.textContent = "";
      }, 10000);
    })
    .catch((error) => {
      generateResult.textContent = "Erreur lors de l'envoi du modèle.";
      console.error("Erreur lors de l'envoi du modèle : ", error);
    });
});

downloadAudio.addEventListener("click", () => {
  const downloadLink = document.getElementById("download-link");

  fetch("/generate/download", {
    method: "GET",
  })
    .then((response) => response.blob())
    .then((blob) => {
      const url = window.URL.createObjectURL(blob);
      downloadLink.href = url;
      downloadLink.download = "output.wav";
      downloadLink.click();
      window.URL.revokeObjectURL(url);
    })
    .catch((error) => {
      console.error("Erreur lors du téléchargement : ", error);
    });
});
