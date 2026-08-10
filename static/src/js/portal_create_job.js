// File: static/src/js/portal_create_job.js
// Pattern: select bình thường + nút + mở modal tạo mới (giống Odoo backend)
(function () {
    'use strict';

    // ─── API endpoints ────────────────────────────────────────────────────────
    var API_URLS = {
        salary_level: '/my/recruitment/api/create/salary_level',
        location: '/my/recruitment/api/create/location',
        degree: '/my/recruitment/api/create/degree',
        skill: '/my/recruitment/api/create/skill',
    };

    // ─── Cấu hình modal cho từng loại ────────────────────────────────────────
    var MODAL_CONFIG = {
        salary_level: {
            title: 'Tạo mức lương mới',
            html: function () {
                return '<div class="mb-3">'
                    + '<label class="form-label">Tên mức lương <span class="text-danger">*</span></label>'
                    + '<input type="text" id="qc_name" class="form-control" placeholder="VD: 10-15 triệu">'
                    + '</div>'
                    + '<div class="row">'
                    + '<div class="col-6"><div class="mb-3">'
                    + '<label class="form-label">Lương tối thiểu (VND)</label>'
                    + '<input type="number" id="qc_min" class="form-control" placeholder="10000000">'
                    + '</div></div>'
                    + '<div class="col-6"><div class="mb-3">'
                    + '<label class="form-label">Lương tối đa (VND)</label>'
                    + '<input type="number" id="qc_max" class="form-control" placeholder="15000000">'
                    + '</div></div>'
                    + '</div>';
            },
            getData: function () {
                return {
                    name: (document.getElementById('qc_name') || {}).value.trim(),
                    min_salary: (document.getElementById('qc_min') || {}).value || 0,
                    max_salary: (document.getElementById('qc_max') || {}).value || 0,
                };
            },
        },

        location: {
            title: 'Tạo địa điểm mới',
            html: function () {
                return '<div class="mb-3">'
                    + '<label class="form-label">Tỉnh/Thành phố <span class="text-danger">*</span></label>'
                    + '<select id="qc_state_id" class="form-control" required>'
                    + '<option value="">-- Chọn tỉnh/thành phố --</option>'
                    + '</select>'
                    + '</div>'
                    + '<div class="mb-3">'
                    + '<label class="form-label">Phường/Xã</label>'
                    + '<select id="qc_ward_id" class="form-control">'
                    + '<option value="">-- Chọn phường/xã --</option>'
                    + '</select>'
                    + '</div>';
            },
            getData: function () {
                return {
                    state_id: (document.getElementById('qc_state_id') || {}).value,
                    ward_id: (document.getElementById('qc_ward_id') || {}).value,
                };
            },
            onShow: function () {
                var stateSelect = document.getElementById('qc_state_id');
                var wardSelect = document.getElementById('qc_ward_id');
                if (!stateSelect || !wardSelect) return;

                fetch('/hr_recruitment/api/states', {
                    headers: {'Content-Type': 'application/json'}
                })
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        stateSelect.innerHTML = '<option value="">-- Chọn tỉnh/thành phố --</option>';
                        if (data.states) {
                            data.states.forEach(function (s) {
                                var opt = document.createElement('option');
                                opt.value = s.id;
                                opt.textContent = s.name;
                                stateSelect.appendChild(opt);
                            });
                        }
                    });

                stateSelect.onchange = function () {
                    var stateId = stateSelect.value;
                    wardSelect.innerHTML = '<option value="">-- Chọn phường/xã --</option>';
                    if (!stateId) return;
                    fetch('/hr_recruitment/api/wards?state_id=' + encodeURIComponent(stateId), {
                        headers: {'Content-Type': 'application/json'}
                    })
                        .then(function (r) { return r.json(); })
                        .then(function (data) {
                            (data.wards || []).forEach(function (w) {
                                var opt = document.createElement('option');
                                opt.value = w.id;
                                opt.textContent = w.name;
                                wardSelect.appendChild(opt);
                            });
                        })
                        .catch(function () {});
                };
            }
        },
        degree: {
            title: 'Tạo trình độ mới',
            html: function () {
                return '<div class="mb-3">'
                    + '<label class="form-label">Tên trình độ <span class="text-danger">*</span></label>'
                    + '<input type="text" id="qc_name" class="form-control" placeholder="VD: Đại học">'
                    + '</div>';
            },
            getData: function () {
                return {name: (document.getElementById('qc_name') || {}).value.trim()};
            },
        },

        skill: {
            title: 'Tạo kỹ năng mới',
            html: function (prefill) {
                return '<div class="mb-3">'
                    + '<label class="form-label">Tên kỹ năng <span class="text-danger">*</span></label>'
                    + '<input type="text" id="qc_name" class="form-control" placeholder="VD: Python" value="' + (prefill || '') + '">'
                    + '</div>'
                    + '<div class="mb-3">'
                    + '<label class="form-label">Loại kỹ năng <span class="text-danger">*</span></label>'
                    + '<select id="qc_skill_type" class="form-select">'
                    + '<option value="">-- Đang tải... --</option>'
                    + '</select>'
                    + '</div>';
            },
            getData: function () {
                return {
                    name: (document.getElementById('qc_name') || {}).value.trim(),
                    skill_type_id: (document.getElementById('qc_skill_type') || {}).value,
                };
            },
        },
    };

    // ─── State ────────────────────────────────────────────────────────────────
    var bsModal = null;
    var currentType = null;
    var currentCallback = null;

    // ─── Init ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
    initSkillField();
    initEditors();
    initPortalForms();
});

    // Dùng event delegation trên document để không bị ảnh hưởng bởi thời điểm render
    document.addEventListener('click', function (e) {
        // Nút Lưu trong modal
        if (e.target.closest('#qcModalSave')) {
            submitModal();
            return;
        }
        // Nút Hủy / X (data-bs-dismiss="modal")
        if (e.target.closest('[data-bs-dismiss="modal"]')) {
            modalHide();
            return;
        }
        // Click ra ngoài backdrop để đóng modal
        if (e.target.id === 'qc-backdrop') {
            modalHide();
        }
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
            var modal = document.getElementById('quickCreateModal');
            if (modal && modal.classList.contains('show')) {
                e.preventDefault();
                submitModal();
            }
        }
        if (e.key === 'Escape') {
            var modal = document.getElementById('quickCreateModal');
            if (modal && modal.classList.contains('show')) {
                modalHide();
            }
        }
    });

    // ─── Modal helpers (không dùng bootstrap.Modal global) ──────────────────
    function getModal() {
        return document.getElementById('quickCreateModal');
    }

    function modalShow() {
        var el = getModal();
        if (!el) return;
        el.style.display = 'block';
        el.classList.add('show');
        document.body.classList.add('modal-open');
        // backdrop
        var bd = document.getElementById('qc-backdrop');
        if (!bd) {
            bd = document.createElement('div');
            bd.id = 'qc-backdrop';
            bd.className = 'modal-backdrop fade show';
            document.body.appendChild(bd);
        }
        // focus first input
        setTimeout(function () {
            var inp = el.querySelector('#qcModalBody input');
            if (inp) inp.focus();
        }, 100);
    }

    function modalHide() {
        var el = getModal();
        if (!el) return;
        el.style.display = '';
        el.classList.remove('show');
        document.body.classList.remove('modal-open');
        var bd = document.getElementById('qc-backdrop');
        if (bd) bd.remove();
    }

    // ─── Public: mở modal (gọi từ onclick trong template) ────────────────────
    window.openCreateModal = function (type, prefill) {
        var cfg = MODAL_CONFIG[type];
        if (!cfg) return;

        currentType = type;
        currentCallback = null;  // reset, sẽ set tuỳ loại

        document.getElementById('qcModalTitle').innerHTML =
            '<i class="fa fa-plus-circle me-2"></i>' + cfg.title;
        document.getElementById('qcModalBody').innerHTML = cfg.html(prefill || '');
        document.getElementById('qcModalError').classList.add('d-none');

        modalShow();

        setTimeout(function () {
            var first = document.querySelector('#qcModalBody input');
            if (first) first.focus();
        }, 300);

        // Callback theo loại: sau khi lưu thành công
        // Load skill types khi mở modal skill
        if (type === 'skill') {
            loadSkillTypes();
        }

        currentCallback = function (id, name) {
            if (type === 'salary_level') {
                addOptionAndSelect('salary_level_select', id, name);
            } else if (type === 'location') {
                addOptionAndSelect('location_select', id, name);
            } else if (type === 'degree') {
                addOptionAndSelect('degree_select', id, name);
            } else if (type === 'skill') {
                addSkillTag(id, name);
                addSkillOption(id, name);
            }
            showToast('Đã tạo: ' + name);
        };
    };

    // ─── Submit modal ─────────────────────────────────────────────────────────
    function submitModal() {
        var cfg = MODAL_CONFIG[currentType];
        if (!cfg) return;

        var data = cfg.getData();
        if (!data.name) {
            showModalError('Vui lòng nhập đầy đủ thông tin bắt buộc');
            return;
        }

        var saveBtn = document.getElementById('qcModalSave');
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fa fa-spinner fa-spin me-1"></i>Đang lưu...';

        callApi(API_URLS[currentType], data, function (result) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="fa fa-save me-1"></i>Lưu';

            modalHide();
            if (currentCallback) currentCallback(result.id, result.name);
        }, function (errMsg) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="fa fa-save me-1"></i>Lưu';
            showModalError(errMsg);
        });
    }

    // ─── Helper: thêm option vào <select> và tự chọn nó ─────────────────────
    function addOptionAndSelect(selectId, id, name) {
        var sel = document.getElementById(selectId);
        if (!sel) return;
        // Kiểm tra trùng
        if (sel.querySelector('option[value="' + id + '"]')) {
            sel.value = id;
            return;
        }
        var opt = new Option(name, id, true, true);
        sel.appendChild(opt);
        sel.value = id;
    }

    // ═════════════════════════════════════════════════════════════════════════
    //  SKILL MANY2MANY TAG FIELD
    // ═════════════════════════════════════════════════════════════════════════
    var skillSelected = new Set();   // Set<string> của id đã chọn
    var skillAllOpts = [];          // [{id, label, el}] cache options

    function initSkillField() {
        var dropdown = document.getElementById('skill_dropdown');
        var searchInp = document.getElementById('skill_search_input');
        if (!dropdown || !searchInp) return;

        // Cache
        skillAllOpts = Array.from(dropdown.querySelectorAll('li')).map(function (li) {
            return {id: String(li.dataset.id), label: li.dataset.label, el: li};
        });

        // Pre-load selected skills (for edit page) - defer slightly to ensure inline script ran
        setTimeout(function() {
            if (window._preselectedSkills && Array.isArray(window._preselectedSkills)) {
                window._preselectedSkills.forEach(function(skill) {
                    if (skill && skill.id && skill.label) {
                        addSkillTag(String(skill.id), skill.label);
                    }
                });
            }
        }, 300);

        // Search input
        searchInp.addEventListener('focus', function () {
            filterSkillDropdown(this.value);
            dropdown.classList.remove('d-none');
        });

        searchInp.addEventListener('input', function () {
            filterSkillDropdown(this.value);
            dropdown.classList.remove('d-none');
        });

        // Click chọn từ dropdown
        dropdown.addEventListener('mousedown', function (e) {
            var li = e.target.closest('li');
            if (!li || li.classList.contains('sd-no-result')) return;
            e.preventDefault();
            addSkillTag(li.dataset.id, li.dataset.label);
            searchInp.value = '';
            filterSkillDropdown('');
            dropdown.classList.add('d-none');
        });

        // Đóng dropdown khi click ngoài
        document.addEventListener('click', function (e) {
            var skillField = document.getElementById('skill_field');
            if (skillField && !skillField.contains(e.target)) {
                dropdown.classList.add('d-none');
            }
        });
    }

    function filterSkillDropdown(q) {
        var q_lo = (q || '').toLowerCase();
        var visible = 0;
        skillAllOpts.forEach(function (opt) {
            if (skillSelected.has(opt.id)) {
                opt.el.style.display = 'none';
                return;
            }
            var match = !q_lo || opt.label.toLowerCase().includes(q_lo);
            opt.el.style.display = match ? '' : 'none';
            if (match) visible++;
        });

        var noResult = document.getElementById('sd_no_result');
        if (visible === 0) {
            if (!noResult) {
                noResult = document.createElement('li');
                noResult.id = 'sd_no_result';
                noResult.className = 'sd-no-result';
                document.getElementById('skill_dropdown').appendChild(noResult);
            }
            noResult.textContent = q_lo
                ? 'Không tìm thấy "' + q + '" — bấm "Tạo mới" để thêm'
                : 'Chưa có kỹ năng nào';
        } else if (noResult) {
            noResult.remove();
        }
    }

    // Thêm tag vào UI + sinh hidden input
    function addSkillTag(id, label) {
        id = String(id);
        if (skillSelected.has(id)) return;
        skillSelected.add(id);

        // Hidden input
        var form = document.getElementById('job_form') || document.getElementById('job_edit_form');
        if (form) {
            var inp = document.createElement('input');
            inp.type = 'hidden';
            inp.name = 'skill_ids';
            inp.value = id;
            inp.id = 'skill_hidden_' + id;
            form.appendChild(inp);
        }

        // Tag chip
        var tagsWrap = document.getElementById('skill_tags_wrap');
        if (tagsWrap) {
            var tag = document.createElement('span');
            tag.className = 'm2m-tag';
            tag.dataset.id = id;
            tag.innerHTML = label
                + ' <button type="button" class="m2m-tag-remove" title="Xóa">×</button>';
            tag.querySelector('.m2m-tag-remove').addEventListener('click', function () {
                removeSkillTag(id);
            });
            tagsWrap.appendChild(tag);
        }

        // Ẩn khỏi dropdown
        skillAllOpts.forEach(function (o) {
            if (o.id === id) o.el.style.display = 'none';
        });
    }

    function removeSkillTag(id) {
        id = String(id);
        skillSelected.delete(id);

        var inp = document.getElementById('skill_hidden_' + id);
        if (inp) inp.remove();

        var tag = document.querySelector('#skill_tags_wrap .m2m-tag[data-id="' + id + '"]');
        if (tag) tag.remove();

        // Hiện lại trong dropdown nếu khớp filter hiện tại
        skillAllOpts.forEach(function (o) {
            if (o.id === id) {
                var q = document.getElementById('skill_search_input').value;
                o.el.style.display = (!q || o.label.toLowerCase().includes(q.toLowerCase())) ? '' : 'none';
            }
        });
    }

    // Thêm option mới vào cache + DOM dropdown (dùng sau khi tạo mới)
    function addSkillOption(id, name) {
        id = String(id);
        var dropdown = document.getElementById('skill_dropdown');
        var li = document.createElement('li');
        li.dataset.id = id;
        li.dataset.label = name;
        li.textContent = name;
        li.style.display = 'none'; // vừa được chọn thành tag rồi, ẩn đi
        dropdown.appendChild(li);
        skillAllOpts.push({id: id, label: name, el: li});
    }

    // ─── Load skill types vào dropdown ───────────────────────────────────────
    function loadSkillTypes() {
        fetch('/my/recruitment/api/skill_types', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({jsonrpc: '2.0', method: 'call', params: {}}),
        })
            .then(function (r) {
                return r.json();
            })
            .then(function (data) {
                var sel = document.getElementById('qc_skill_type');
                if (!sel) return;
                var types = data.result || [];
                sel.innerHTML = '<option value="">-- Chọn loại kỹ năng --</option>'
                    + types.map(function (t) {
                        return '<option value="' + t.id + '">' + t.name + '</option>';
                    }).join('');
            })
            .catch(function () {
            });
    }

    // ═════════════════════════════════════════════════════════════════════════
    //  API HELPER
    // ═════════════════════════════════════════════════════════════════════════
    function callApi(url, params, onSuccess, onError) {
        fetch(url, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({jsonrpc: '2.0', method: 'call', params: params}),
        })
            .then(function (r) {
                return r.json();
            })
            .then(function (data) {
                var result = data.result;
                if (result && result.success) {
                    onSuccess(result);
                } else {
                    var msg = (result && result.error) || 'Đã xảy ra lỗi, vui lòng thử lại';
                    onError(msg);
                }
            })
            .catch(function () {
                onError('Lỗi kết nối, vui lòng thử lại');
            });
    }

    // ─── UI helpers ───────────────────────────────────────────────────────────
    function showModalError(msg) {
        var el = document.getElementById('qcModalError');
        el.textContent = msg;
        el.classList.remove('d-none');
    }

    function showToast(msg) {
        document.getElementById('qc-toast-msg').textContent = msg;
        var toastEl = document.getElementById('qc-toast');
        if (toastEl) {
            toastEl.classList.add('show');
            setTimeout(function () {
                toastEl.classList.remove('show');
            }, 3000);
        }
    }

})();
// style text
function createSimpleEditor(textarea) {
    if (textarea.dataset.editorInitialized) return;
    textarea.dataset.editorInitialized = 'true';

    var placeholder = textarea.getAttribute('placeholder') || 'Nhập nội dung...';
    var targetId = textarea.dataset.target;
    var hiddenTextarea = targetId ? document.getElementById(targetId) : textarea;
    if (!hiddenTextarea) return;

    var wrapper = document.createElement('div');
    wrapper.className = 'simple-rich-editor';
    wrapper.style.cssText = 'border:1px solid #ced4da;border-radius:0.375rem;overflow:hidden;background:#fff;';

    var toolbar = document.createElement('div');
    toolbar.style.cssText = 'display:flex;flex-wrap:wrap;gap:2px;padding:6px 8px;background:#f8f9fa;border-bottom:1px solid #dee2e6;';

    var btnDefs = [
        {cmd: 'bold', icon: '<b>B</b>', title: 'Bold'},
        {cmd: 'italic', icon: '<i>I</i>', title: 'Italic'},
        {cmd: 'underline', icon: '<u>U</u>', title: 'Underline'},
        {cmd: 'strikeThrough', icon: '<s>S</s>', title: 'Gạch ngang'},
        {cmd: 'sep'},
        {cmd: 'insertOrderedList', icon: '1.', title: 'Danh sách số'},
        {cmd: 'insertUnorderedList', icon: '&#8226;', title: 'Danh sách chấm'},
        {cmd: 'sep'},
        {cmd: 'formatBlock', value: 'H2', icon: 'H2', title: 'Tiêu đề 2'},
        {cmd: 'formatBlock', value: 'H3', icon: 'H3', title: 'Tiêu đề 3'},
        {cmd: 'formatBlock', value: 'P', icon: 'P', title: 'Đoạn văn'},
        {cmd: 'sep'},
        {cmd: 'removeFormat', icon: '&#10006;', title: 'Xóa định dạng'},
    ];

    btnDefs.forEach(function (def) {
        if (def.cmd === 'sep') {
            var s = document.createElement('span');
            s.style.cssText = 'width:1px;background:#dee2e6;margin:2px 4px;display:inline-block;align-self:stretch;';
            toolbar.appendChild(s);
            return;
        }
        var b = document.createElement('button');
        b.type = 'button';
        b.title = def.title;
        b.innerHTML = def.icon;
        b.style.cssText = 'min-width:30px;height:28px;padding:0 6px;border:1px solid #ced4da;border-radius:4px;background:#fff;cursor:pointer;font-size:13px;color:#333;line-height:1;';
        b.addEventListener('mousedown', function (e) {
            e.preventDefault();
            document.execCommand(def.cmd, false, def.value || null);
            ed.focus();
        });
        b.addEventListener('mouseover', function () {
            b.style.background = '#e9ecef';
        });
        b.addEventListener('mouseout', function () {
            b.style.background = '#fff';
        });
        toolbar.appendChild(b);
    });

    var ed = document.createElement('div');
    ed.contentEditable = 'true';
    ed.style.cssText = 'min-height:160px;padding:10px 14px;outline:none;font-size:14px;line-height:1.6;color:#212529;';

    function setPlaceholder() {
        ed.innerHTML = '<span style="color:#6c757d;pointer-events:none;">' + placeholder + '</span>';
        ed.dataset.empty = 'true';
    }

    function clearPlaceholder() {
        if (ed.dataset.empty === 'true') {
            ed.innerHTML = '';
            ed.dataset.empty = 'false';
        }
    }

    function syncToHidden() {
        if (ed.dataset.empty !== 'true') {
            hiddenTextarea.value = ed.innerHTML;
        } else {
            hiddenTextarea.value = '';
        }
    }

    hiddenTextarea.value ? (ed.innerHTML = hiddenTextarea.value, ed.dataset.empty = 'false') : setPlaceholder();

    ed.addEventListener('focus', function () {
        clearPlaceholder();
        wrapper.style.borderColor = '#86b7fe';
        wrapper.style.boxShadow = '0 0 0 0.25rem rgba(13,110,253,.25)';
    });
    ed.addEventListener('blur', function () {
        wrapper.style.borderColor = '#ced4da';
        wrapper.style.boxShadow = 'none';
        if (!ed.innerHTML || ed.innerHTML === '<br>') setPlaceholder();
        syncToHidden();
    });
    ed.addEventListener('input', syncToHidden);

    wrapper.appendChild(toolbar);
    wrapper.appendChild(ed);
    textarea.parentNode.insertBefore(wrapper, textarea);
    textarea.style.display = 'none';

    var form = textarea.closest('form');
    if (form && !form.dataset.editorSyncAdded) {
        form.dataset.editorSyncAdded = 'true';
        form.addEventListener('submit', function () {
            document.querySelectorAll('textarea.sre-target[data-editor-initialized]').forEach(function (ta) {
                var hid = document.getElementById(ta.dataset.target);
                var w = ta.previousElementSibling;
                if (hid && w) {
                    var e2 = w.querySelector('[contenteditable]');
                    if (e2 && e2.dataset.empty !== 'true') hid.value = e2.innerHTML;
                }
            });
        });
    }
}


// ═════════════════════════════════════════════════════════════════════════════
//  PHOTO PREVIEW
// ═════════════════════════════════════════════════════════════════════════════
document.addEventListener('change', function (e) {
    // Kiểm tra xem phần tử thay đổi có phải là ô chọn ảnh hay không
    if (e.target && e.target.id === 'job_photo_input') {
        var fileInput = e.target;
        var file = fileInput.files && fileInput.files[0];
        var previewImg  = document.getElementById('photo_preview_img');
        var previewIcon = document.getElementById('photo_preview_icon');
        var previewWrap = document.getElementById('photo_preview_wrap');

        if (!previewImg) return;

        if (file) {
            // Kiểm tra dung lượng ảnh (> 2MB)
            if (file.size > 2 * 1024 * 1024) {
                alert('Ảnh quá lớn! Vui lòng chọn ảnh nhỏ hơn 2MB.');
                fileInput.value = '';

                // Reset preview về mặc định
                previewImg.src = '';
                previewImg.style.display = 'none';
                if (previewIcon) previewIcon.style.display = '';
                if (previewWrap) previewWrap.style.border = '2px dashed #ced4da';
                return;
            }

            // Đọc file và hiển thị Preview
            var reader = new FileReader();
            reader.onload = function (event) {
                previewImg.src = event.target.result;
                previewImg.style.display = 'block';
                if (previewIcon) previewIcon.style.display = 'none';
                if (previewWrap) previewWrap.style.border = '2px solid #1E3769';
            };
            reader.readAsDataURL(file);
        } else {
            // Trường hợp người dùng hủy chọn file
            previewImg.src = '';
            previewImg.style.display = 'none';
            if (previewIcon) previewIcon.style.display = '';
            if (previewWrap) previewWrap.style.border = '2px dashed #ced4da';
        }
    }
});


function initPortalForms() {
    ['job_form', 'job_edit_form'].forEach(function (formId) {
        var form = document.getElementById(formId);
        if (!form) return;
        var stateEl = form.querySelector('select[name="state_id"]');
        var wardEl = form.querySelector('select[name="ward_id"]');
        if (!stateEl || !wardEl) return;

        stateEl.addEventListener('change', function () {
            var stateId = stateEl.value;
            wardEl.innerHTML = '<option value="">-- Chọn phường/xã --</option>';
            if (!stateId) return;
            fetch('/hr_recruitment/api/wards?state_id=' + encodeURIComponent(stateId), {
                headers: {'Content-Type': 'application/json'}
            })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    (data.wards || []).forEach(function (w) {
                        var opt = new Option(w.name, w.id, false, false);
                        wardEl.appendChild(opt);
                    });
                })
                .catch(function () {});
        });
    });
}

function initEditors() {
    if (window._editPrefill) {
        var p = window._editPrefill;
        var hDesc = document.getElementById('hidden_description');
        var hReq  = document.getElementById('hidden_requirements');
        var hBen  = document.getElementById('hidden_benefits');
        if (hDesc && p.description) hDesc.value = p.description;
        if (hReq  && p.requirements) hReq.value = p.requirements;
        if (hBen  && p.benefits)     hBen.value = p.benefits;
    }

    document.querySelectorAll('textarea.sre-target').forEach(createSimpleEditor);
}
window.addEventListener('load', initEditors);