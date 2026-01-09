$(function () {
    const contentSection = document.querySelector('.content');
    const SERVICE_STATUS_URL = contentSection.dataset.serviceStatusUrl;
    const BULK_REMOVE_URL = contentSection.dataset.bulkRemoveUrl;
    const REMOVE_USER_URL_TEMPLATE = contentSection.dataset.removeUserUrlTemplate;
    const BULK_ADD_URL = contentSection.dataset.bulkAddUrl;
    const ADD_USER_URL = contentSection.dataset.addUserUrl;
    const EDIT_USER_URL_TEMPLATE = contentSection.dataset.editUserUrlTemplate;
    const RESET_USER_URL_TEMPLATE = contentSection.dataset.resetUserUrlTemplate;
    const USER_URI_URL_TEMPLATE = contentSection.dataset.userUriUrlTemplate;
    const BULK_URI_URL = contentSection.dataset.bulkUriUrl;
    const USERS_BASE_URL = contentSection.dataset.usersBaseUrl;
    const GET_USER_URL_TEMPLATE = contentSection.dataset.getUserUrlTemplate;
    const SEARCH_USERS_URL = contentSection.dataset.searchUrl;

    const usernameRegex = /^[a-zA-Z0-9_]+$/;
    const passwordRegex = /^[a-zA-Z0-9]+$/;
    let cachedUserData = [];
    let searchTimeout = null;
    const PRACTICAL_MAX_DAYS = 36500;

    // Toast helper
    function toast(type, message, timer = 3000) {
        Swal.fire({
            icon: type,
            title: message,
            toast: true,
            position: 'top-end',
            showConfirmButton: false,
            timer: timer,
            timerProgressBar: true,
            didOpen: (t) => {
                t.addEventListener('mouseenter', Swal.stopTimer);
                t.addEventListener('mouseleave', Swal.resumeTimer);
            }
        });
    }

    function setCookie(name, value, days) {
        let expires = "";
        if (days) {
            const date = new Date();
            date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
            expires = "; expires=" + date.toUTCString();
        }
        document.cookie = name + "=" + (value || "") + expires + "; path=/";
    }

    function getCookie(name) {
        const nameEQ = name + "=";
        const ca = document.cookie.split(';');
        for (let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) === ' ') c = c.substring(1, c.length);
            if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
        }
        return null;
    }

    function generatePassword(length = 32) {
        const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
        let result = '';
        for (let i = 0; i < length; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return result;
    }

    function checkIpLimitServiceStatus() {
        $.getJSON(SERVICE_STATUS_URL)
            .done(data => {
                if (data.hysteria_iplimit === true) {
                    $('.requires-iplimit-service').show();
                }
            })
            .fail(() => console.error('Error fetching IP limit service status.'));
    }

    function validateUsername(inputElement, errorElement) {
        const username = $(inputElement).val();
        const isValid = usernameRegex.test(username);
        $(errorElement).text(isValid ? "" : "Usernames can only contain letters, numbers, and underscores.");
        $(inputElement).closest('form').find('button[type="submit"]').prop('disabled', !isValid);
        return isValid;
    }
    
    function validatePassword(inputElement, errorElement) {
        const password = $(inputElement).val();
        const isValid = password === '' || passwordRegex.test(password);
        $(errorElement).text(isValid ? "" : "Password can only contain letters and numbers.");
        $('#editSubmitButton').prop('disabled', !isValid);
        return isValid;
    }
    
    function validateExpirationDays(inputElement, errorElement) {
        const days = parseInt($(inputElement).val(), 10);
        let isValid = !isNaN(days) && days >= 0;
        let errorMessage = "";

        if (!isValid) {
            errorMessage = "Please enter a non-negative number.";
        } else if (days > PRACTICAL_MAX_DAYS) {
            isValid = false;
            errorMessage = `For unlimited duration, please use 0. Values above ${PRACTICAL_MAX_DAYS} are not practical.`;
        }

        $(errorElement).text(errorMessage);
        $(inputElement).closest('form').find('button[type="submit"]').prop('disabled', !isValid);
        return isValid;
    }

    function refreshUserList() {
        const query = $("#searchInput").val().trim();
        if (query !== "") {
            performSearch();
        } else {
            restoreInitialView();
        }
    }

    function performSearch() {
        const query = $("#searchInput").val().trim();
        const $userTableBody = $("#userTableBody");
        const $paginationContainer = $("#paginationContainer");
        const $userTotalCount = $("#user-total-count");

        $paginationContainer.hide();
        $userTableBody.css('opacity', 0.5).html('<tr><td colspan="14" class="text-center p-4"><i class="fas fa-spinner fa-spin"></i> Searching...</td></tr>');

        $.ajax({
            url: SEARCH_USERS_URL,
            type: 'GET',
            data: { q: query },
            success: function (data) {
                $userTableBody.html(data);
                checkIpLimitServiceStatus();
                const resultCount = $userTableBody.find('tr.user-main-row').length;
                $userTotalCount.text(resultCount);
            },
            error: function () {
                toast('error', 'Search failed');
                $userTableBody.html('<tr><td colspan="14" class="text-center p-4 text-danger">Search failed to load.</td></tr>');
            },
            complete: function () {
                $userTableBody.css('opacity', 1);
            }
        });
    }

    function restoreInitialView() {
        const $userTableBody = $("#userTableBody");
        const $paginationContainer = $("#paginationContainer");
        const $userTotalCount = $("#user-total-count");

        $userTableBody.css('opacity', 0.5).html('<tr><td colspan="14" class="text-center p-4"><i class="fas fa-spinner fa-spin"></i> Loading users...</td></tr>');

        $.ajax({
            url: USERS_BASE_URL,
            type: 'GET',
            success: function (data) {
                const newBody = $(data).find('#userTableBody').html();
                const newPagination = $(data).find('#paginationContainer').html();
                const newTotalCount = $(data).find('#user-total-count').text();

                $userTableBody.html(newBody);
                $paginationContainer.html(newPagination).show();
                $userTotalCount.text(newTotalCount);

                checkIpLimitServiceStatus();
            },
            error: function () {
                toast('error', 'Failed to load users');
                $userTableBody.html('<tr><td colspan="14" class="text-center p-4 text-danger">Failed to load users. Please refresh the page.</td></tr>');
            },
            complete: function () {
                $userTableBody.css('opacity', 1);
            }
        });
    }
    
    $('#editPassword').on('input', function() {
        validatePassword(this, '#editPasswordError');
    });

    $('#addUsername, #addBulkPrefix').on('input', function() {
        validateUsername(this, `#${this.id}Error`);
    });

    $('#addExpirationDays, #addBulkExpirationDays, #editExpirationDays').on('input', function() {
        validateExpirationDays(this, `#${this.id}Error`);
    });

    $(".filter-button").on("click", function (e) {
        e.preventDefault();
        const filter = $(this).data("filter");
        
        // Update active state on filter buttons
        $(".btn-group-filters .btn-filter").removeClass("active");
        $(".btn-group-filters .btn-filter[data-filter='" + filter + "']").addClass("active");
        
        $("#selectAll").prop("checked", false);
        $("#userTable tbody tr.user-main-row").each(function () {
            let showRow;
            switch (filter) {
                case "on-hold":    showRow = $(this).find("td.status-cell i").hasClass("text-warning"); break;
                case "online":     showRow = $(this).find("td.status-cell i").hasClass("text-success"); break;
                case "enable":     showRow = $(this).find("td.enable-cell i").hasClass("text-success"); break;
                case "disable":    showRow = $(this).find("td.enable-cell i").hasClass("text-danger"); break;
                default:           showRow = true;
            }
            $(this).toggle(showRow).find(".user-checkbox").prop("checked", false);
            if (!showRow) {
                $(this).next('tr.user-details-row').hide();
            }
        });
    });

    $("#selectAll").on("change", function () {
        $("#userTable tbody tr.user-main-row:visible .user-checkbox").prop("checked", this.checked);
    });

    $("#deleteSelected").on("click", function () {
        const selectedUsers = $(".user-checkbox:checked").map((_, el) => $(el).val()).get();
        if (selectedUsers.length === 0) {
            return toast('warning', 'Select at least one user');
        }
        Swal.fire({
            title: "Delete users?",
            html: `<small>This will delete: <b>${selectedUsers.join(", ")}</b></small>`,
            icon: "warning",
            showCancelButton: true,
            confirmButtonColor: "#ef4444",
            confirmButtonText: "Delete",
            cancelButtonText: "Cancel"
        }).then((result) => {
            if (!result.isConfirmed) return;

            if (selectedUsers.length > 1) {
                $.ajax({
                    url: BULK_REMOVE_URL,
                    method: "POST",
                    contentType: "application/json",
                    data: JSON.stringify({ usernames: selectedUsers })
                })
                .done(() => { toast('success', 'Users deleted'); refreshUserList(); })
                .fail((err) => toast('error', err.responseJSON?.detail || 'Delete failed'));
            } else {
                const singleUrl = REMOVE_USER_URL_TEMPLATE.replace('U', selectedUsers[0]);
                $.ajax({ url: singleUrl, method: "DELETE" })
                .done(() => { toast('success', 'User deleted'); refreshUserList(); })
                .fail((err) => toast('error', err.responseJSON?.detail || 'Delete failed'));
            }
        });
    });

    $("#addUserForm, #addBulkUsersForm").on("submit", function (e) {
        e.preventDefault();
        const form = $(this);
        const isBulk = form.attr('id') === 'addBulkUsersForm';
        const url = isBulk ? BULK_ADD_URL : ADD_USER_URL;
        const button = form.find('button[type="submit"]').prop('disabled', true);
        
        const formData = new FormData(this);
        const jsonData = Object.fromEntries(formData.entries());
        jsonData.unlimited = jsonData.unlimited === 'on';
        
        // Handle max_ips - convert to int or null
        if (jsonData.max_ips !== undefined && jsonData.max_ips !== '') {
            jsonData.max_ips = parseInt(jsonData.max_ips);
        } else {
            delete jsonData.max_ips;
        }

        $.ajax({
            url: url,
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify(jsonData),
        })
        .done(res => {
            $('#addUserModal').modal('hide');
            toast('success', res.detail || 'User added');
            refreshUserList();
        })
        .fail(err => toast('error', err.responseJSON?.detail || 'Failed to add user'))
        .always(() => button.prop('disabled', false));
    });

    $("#editUserModal").on("show.bs.modal", function (event) {
        const user = $(event.relatedTarget).data("user");
        const dataRow = $(event.relatedTarget).closest("tr.user-main-row");
        const url = GET_USER_URL_TEMPLATE.replace('U', user);

        const trafficText = dataRow.find("td.traffic-cell").text();
        const usageDaysText = dataRow.find("td.usage-days-cell").text();
        const expiryText = usageDaysText.split('/')[1] || "0";
        const note = dataRow.data('note');
        const statusText = dataRow.find("td.status-cell").text().trim();
        
        $('#editPasswordError').text('');
        $('#editExpirationDaysError').text('');
        $('#editSubmitButton').prop('disabled', false);

        $("#originalUsername").val(user);
        $("#editUsername").val(user);
        $("#editTrafficLimit").val(parseFloat(trafficText.split('/')[1]) || 0);

        if (statusText.includes("On-hold")) {
            $("#editExpirationDays").val('').attr("placeholder", "Paused");
        } else {
            $("#editExpirationDays").val(parseInt(expiryText) || 0).attr("placeholder", "");
        }
        
        $("#editNote").val(note || '');
        $("#editBlocked").prop("checked", !dataRow.find("td.enable-cell i").hasClass("text-success"));
        $("#editUnlimitedIp").prop("checked", dataRow.find(".unlimited-ip-cell i").hasClass("text-primary"));
    
        const passwordInput = $("#editPassword");
        passwordInput.val("Loading...").prop("disabled", true);
    
        $.getJSON(url)
            .done(userData => {
                passwordInput.val(userData.password || '');
                validatePassword('#editPassword', '#editPasswordError');
                // Set max_ips if present
                if (userData.max_ips !== null && userData.max_ips !== undefined) {
                    $("#editMaxIps").val(userData.max_ips);
                } else {
                    $("#editMaxIps").val('');
                }
            })
            .fail(() => {
                passwordInput.val("").attr("placeholder", "Failed to load");
            })
            .always(() => {
                passwordInput.prop("disabled", false);
            });
    });
    
    $('#editUserModal').on('click', '#generatePasswordBtn', function() {
        $('#editPassword').val(generatePassword()).trigger('input');
    });
    
    $("#editUserForm").on("submit", function (e) {
        e.preventDefault();
        const button = $("#editSubmitButton").prop("disabled", true);
        const originalUsername = $("#originalUsername").val();
        const url = EDIT_USER_URL_TEMPLATE.replace('U', originalUsername);

        const formData = new FormData(this);
        const jsonData = Object.fromEntries(formData.entries());
        jsonData.blocked = jsonData.blocked === 'on';
        jsonData.unlimited_ip = jsonData.unlimited_ip === 'on';
        
        // Handle max_ips - convert to int or null (0 means use global)
        if (jsonData.max_ips !== undefined && jsonData.max_ips !== '') {
            jsonData.max_ips = parseInt(jsonData.max_ips);
        } else {
            delete jsonData.max_ips;
        }

        $.ajax({
            url: url,
            method: "PATCH",
            contentType: "application/json",
            data: JSON.stringify(jsonData),
        })
        .done(res => {
            $('#editUserModal').modal('hide');
            toast('success', res.detail || 'User updated');
            refreshUserList();
        })
        .fail(err => toast('error', err.responseJSON?.detail || 'Update failed'))
        .always(() => button.prop('disabled', false));
    });

    $("#userTable").on("click", ".reset-user, .delete-user", function () {
        const button = $(this);
        const username = button.data("user");
        const isDelete = button.hasClass("delete-user");
        const action = isDelete ? "delete" : "reset";
        const urlTemplate = isDelete ? REMOVE_USER_URL_TEMPLATE : RESET_USER_URL_TEMPLATE;

        Swal.fire({
            title: `${action.charAt(0).toUpperCase() + action.slice(1)} user?`,
            html: `<small>User: <b>${username}</b></small>`,
            icon: "warning",
            showCancelButton: true,
            confirmButtonColor: isDelete ? "#ef4444" : "#f59e0b",
            confirmButtonText: action.charAt(0).toUpperCase() + action.slice(1),
            cancelButtonText: "Cancel"
        }).then((result) => {
            if (!result.isConfirmed) return;

            $.ajax({
                url: urlTemplate.replace("U", encodeURIComponent(username)),
                method: isDelete ? "DELETE" : "GET",
            })
            .done(res => { toast('success', res.detail || `User ${action}ed`); refreshUserList(); })
            .fail(() => toast('error', `Failed to ${action} user`));
        });
    });

    $("#qrcodeModal").on("show.bs.modal", function (event) {
        const username = $(event.relatedTarget).data("username");
        const qrcodesContainer = $("#qrcodesContainer").empty();
        const url = USER_URI_URL_TEMPLATE.replace("U", encodeURIComponent(username));
        
        $.getJSON(url, response => {
            [
                { type: "IPv4", link: response.ipv4 },
                { type: "IPv6", link: response.ipv6 },
                { type: "Normal-SUB", link: response.normal_sub }
            ].forEach(config => {
                if (!config.link) return;
                const qrId = `qrcode-${config.type}`;
                const card = $(`<div class="card d-inline-block m-2"><div class="card-body"><div id="${qrId}" class="mx-auto" style="cursor: pointer;"></div><div class="mt-2 text-center small text-muted font-weight-bold">${config.type}</div></div></div>`);
                qrcodesContainer.append(card);
                new QRCodeStyling({ width: 200, height: 200, data: config.link, margin: 2 }).append(document.getElementById(qrId));
                card.on("click", () => {
                    navigator.clipboard.writeText(config.link).then(() => toast('success', `${config.type} link copied!`, 1500));
                });
            });
        }).fail(() => toast('error', 'Failed to fetch user config'));
    });
    
    $("#showSelectedLinks").on("click", function () {
        const selectedUsers = $(".user-checkbox:checked").map((_, el) => $(el).val()).get();
        if (selectedUsers.length === 0) {
            return toast('warning', 'Select at least one user');
        }
        
        $.ajax({
            url: BULK_URI_URL,
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ usernames: selectedUsers }),
        }).done(results => {
            cachedUserData = results;
            
            const fetchedCount = results.length;
            const failedCount = selectedUsers.length - fetchedCount;
            
            if (failedCount > 0) {
               toast('warning', `Could not fetch ${failedCount} user(s)`);
            }
            
            if (fetchedCount > 0) {
                const hasIPv4 = cachedUserData.some(user => user.ipv4);
                const hasIPv6 = cachedUserData.some(user => user.ipv6);
                const hasNormalSub = cachedUserData.some(user => user.normal_sub);
                const hasNodes = cachedUserData.some(user => user.nodes && user.nodes.length > 0);

                $("#extractIPv4").closest('.form-check-inline').toggle(hasIPv4);
                $("#extractIPv6").closest('.form-check-inline').toggle(hasIPv6);
                $("#extractNormalSub").closest('.form-check-inline').toggle(hasNormalSub);
                $("#extractNodes").closest('.form-check-inline').toggle(hasNodes);

                $("#linksTextarea").val('');
                $("#showLinksModal").modal("show");
            } else {
               toast('error', 'Could not fetch any user info');
            }
        }).fail(() => toast('error', 'Failed to fetch links'));
    });

    $("#extractLinksButton").on("click", function () {
        const allLinks = [];
        const linkTypes = {
            ipv4: $("#extractIPv4").is(":checked"),
            ipv6: $("#extractIPv6").is(":checked"),
            normal_sub: $("#extractNormalSub").is(":checked"),
            nodes: $("#extractNodes").is(":checked")
        };

        cachedUserData.forEach(user => {
            if (linkTypes.ipv4 && user.ipv4) allLinks.push(user.ipv4);
            if (linkTypes.ipv6 && user.ipv6) allLinks.push(user.ipv6);
            if (linkTypes.normal_sub && user.normal_sub) allLinks.push(user.normal_sub);
            if (linkTypes.nodes && user.nodes && user.nodes.length > 0) {
                user.nodes.forEach(node => { if (node.uri) allLinks.push(node.uri); });
            }
        });

        $("#linksTextarea").val(allLinks.join('\n'));
    });
    
    $("#copyExtractedLinksButton").on("click", () => {
        const links = $("#linksTextarea").val();
        if (!links) {
            return toast('info', 'Extract some links first');
        }
        navigator.clipboard.writeText(links).then(() => toast('success', 'Links copied!', 1500));
    });

    $('#userTable').on('click', '.toggle-details-btn', function() {
        const $this = $(this);
        const icon = $this.find('i');
        const detailsRow = $this.closest('tr.user-main-row').next('tr.user-details-row');

        detailsRow.toggle();
        icon.toggleClass('fa-plus fa-minus');
    });
    
    $('#addUserModal').on('show.bs.modal', function () {
        $('#addUserForm, #addBulkUsersForm').trigger('reset');
        $('#addUsernameError, #addBulkPrefixError, #addExpirationDaysError, #addBulkExpirationDaysError').text('');
        Object.assign(document.getElementById('addTrafficLimit'), {value: 30});
        Object.assign(document.getElementById('addExpirationDays'), {value: 30});
        Object.assign(document.getElementById('addBulkTrafficLimit'), {value: 30});
        Object.assign(document.getElementById('addBulkExpirationDays'), {value: 30});
        $('#addSubmitButton, #addBulkSubmitButton').prop('disabled', true);
        const firstTab = document.querySelector('#addUserModal a[data-bs-toggle="tab"]');
        if (firstTab) new bootstrap.Tab(firstTab).show();
    });

    $("#searchButton").on("click", performSearch);
    $("#searchInput").on("keyup", function (e) {
        clearTimeout(searchTimeout);
        const query = $(this).val().trim();

        if (e.key === 'Enter') {
            performSearch();
            return;
        }
        
        if (query === "") {
            searchTimeout = setTimeout(restoreInitialView, 300);
            return;
        }

        searchTimeout = setTimeout(performSearch, 500);
    });

    function initializeLimitSelector() {
        const savedLimit = getCookie('limit') || '50';
        $('#limit-select').val(savedLimit);

        $('#limit-select').on('change', function() {
            const newLimit = $(this).val();
            setCookie('limit', newLimit, 365);
            window.location.href = USERS_BASE_URL;
        });
    }
    
    initializeLimitSelector();
    checkIpLimitServiceStatus();
    
    // Initialize Bootstrap 5 tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    [...tooltipTriggerList].map(el => new bootstrap.Tooltip(el));
});
