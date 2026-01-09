document.addEventListener('DOMContentLoaded', function () {
    const mainContent = document.querySelector('.config-editor-wrapper') || document.querySelector('[data-get-file-url]');
    const GET_FILE_URL = mainContent.dataset.getFileUrl;
    const SET_FILE_URL = mainContent.dataset.setFileUrl;

    const saveButton = document.getElementById("save-button");
    const restoreButton = document.getElementById("restore-button");
    const container = document.getElementById("jsoneditor");

    const editor = new JSONEditor(container, {
        mode: "code",
        onChange: validateJson
    });

    // Toast helper
    function showToast(type, message) {
        Swal.fire({
            icon: type,
            title: message,
            toast: true,
            position: 'top-end',
            showConfirmButton: false,
            timer: 3000,
            timerProgressBar: true,
            didOpen: (toast) => {
                toast.addEventListener('mouseenter', Swal.stopTimer);
                toast.addEventListener('mouseleave', Swal.resumeTimer);
            }
        });
    }

    function validateJson() {
        try {
            editor.get();
            updateSaveButton(true);
        } catch (error) {
            updateSaveButton(false);
        }
    }

    function updateSaveButton(isValid) {
        saveButton.disabled = !isValid;
        if (isValid) {
            saveButton.classList.remove('btn-disabled');
        } else {
            saveButton.classList.add('btn-disabled');
        }
    }

    function saveJson() {
        Swal.fire({
            title: 'Save changes?',
            text: 'This will update the configuration file.',
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'Save',
            cancelButtonText: 'Cancel',
            reverseButtons: true,
            customClass: {
                confirmButton: 'btn btn-primary',
                cancelButton: 'btn btn-secondary'
            }
        }).then((result) => {
            if (result.isConfirmed) {
                fetch(SET_FILE_URL, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(editor.get())
                })
                .then(() => {
                    showToast('success', 'Configuration saved!');
                })
                .catch(error => {
                    showToast('error', 'Failed to save configuration');
                    console.error("Error saving JSON:", error);
                });
            }
        });
    }

    function restoreJson() {
        fetch(GET_FILE_URL)
            .then(response => response.json())
            .then(json => {
                editor.set(json);
                showToast('success', 'Configuration loaded');
            })
            .catch(error => {
                showToast('error', 'Failed to load configuration');
                console.error("Error loading JSON:", error);
            });
    }

    saveButton.addEventListener('click', saveJson);
    restoreButton.addEventListener('click', restoreJson);

    restoreJson();
});
