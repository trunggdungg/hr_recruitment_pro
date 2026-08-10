# -*- coding: utf-8 -*-
import logging
from odoo import http,fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import io
import xlsxwriter
from odoo.tools import html2plaintext
_logger = logging.getLogger(__name__)


class RecruitmentPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super()._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        user = request.env.user
        values['is_recruiter'] = bool(partner.is_recruiter)
        if partner.is_recruiter:
            jobs = request.env['hr.job'].sudo().search([
                ('user_id', '=', user.id)
            ])
            values['recruitment_count'] = len(jobs)
        else:
            values['recruitment_count'] = 0
        return values

    @http.route(['/my/recruitment'], type='http', auth="user", website=True)
    def portal_recruitment(self, **kwargs):
        partner = request.env.user.partner_id
        user = request.env.user

        if not partner.is_recruiter:
            return request.redirect('/')

        active_tab = request.params.get('tab', 'jobs')
        search_query = request.params.get('search', '').strip()
        page = int(request.params.get('page', 1))
        per_page = 10

        # Phân trang ứng viên
        applicant_search = request.params.get('applicant_search', '').strip()
        applicant_page = int(request.params.get('applicant_page', 1))
        applicant_per_page = 10

        # Lấy stage đầu tiên, thường là stage "Mới"
        new_stage = request.env['hr.recruitment.stage'].sudo().search(
            [], order='sequence', limit=1
        )
        applicant_stage_domain = [('stage_id', '!=', new_stage.id)] if new_stage else []

        # Domain tìm kiếm job
        domain = [('user_id', '=', user.id)]
        if search_query:
            domain += [('name', 'ilike', search_query)]

        total_jobs = request.env['hr.job'].sudo().search_count(domain)
        offset = (page - 1) * per_page
        total_pages = max(1, (total_jobs + per_page - 1) // per_page)

        jobs = request.env['hr.job'].sudo().search(
            domain,
            limit=per_page,
            offset=offset,
            order='id desc'
        )

        # Đếm ứng viên theo từng job trên trang hiện tại
        applicant_counts = {}
        for job in jobs:
            applicant_counts[job.id] = request.env['hr.applicant'].sudo().search_count(
                [('job_id', '=', job.id)] + applicant_stage_domain
            )

        # Lấy toàn bộ job của recruiter
        all_job_ids = request.env['hr.job'].sudo().search([
            ('user_id', '=', user.id)
        ]).ids

        # Domain ứng viên với tìm kiếm
        base_applicant_domain = [('job_id', 'in', all_job_ids)] + applicant_stage_domain
        if applicant_search:
            base_applicant_domain += [
                '|', '|',
                ('partner_name', 'ilike', applicant_search),
                ('email_from', 'ilike', applicant_search),
                ('partner_phone', 'ilike', applicant_search)
            ]

        # Đếm tổng ứng viên (trước khi phân trang)
        applicants_count = request.env['hr.applicant'].sudo().search_count(base_applicant_domain)

        # Tính phân trang
        applicant_offset = (applicant_page - 1) * applicant_per_page
        applicant_total_pages = max(1, (applicants_count + applicant_per_page - 1) // applicant_per_page)

        # Lấy ứng viên theo trang
        paginated_applicants = request.env['hr.applicant'].sudo().search(
            base_applicant_domain,
            limit=applicant_per_page,
            offset=applicant_offset,
            order='id desc'
        ) if all_job_ids else request.env['hr.applicant']

        values = {
            'partner': partner,
            'jobs': jobs,
            'applicant_counts': applicant_counts,
            'jobs_count': total_jobs,
            'applicants': paginated_applicants,
            'applicants_count': applicants_count,
            'active_tab': active_tab,
            'page_name': 'recruitment',
            'search_query': search_query,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'total_jobs': total_jobs,
            # Phân trang ứng viên
            'applicant_search': applicant_search,
            'applicant_page': applicant_page,
            'applicant_per_page': applicant_per_page,
            'applicant_total_pages': applicant_total_pages,
        }

        return request.render("eaut_hr_recruitment.portal_my_recruitment", values)

    @http.route('/my/recruitment/job/<int:job_id>/toggle_publish',
                type='json', auth='user', website=True)
    def toggle_job_publish(self, job_id, **kwargs):
        job = request.env['hr.job'].sudo().browse(job_id)
        user = request.env.user

        if not job.exists() or job.user_id.id != user.id:
            return {'error': 'Không có quyền thực hiện'}

        # FIX: chỉ cho phép publish khi đã được duyệt
        if not job.website_published and job.moderation_state != 'approved':
            return {
                'success': False,
                'error': 'Tin tuyển dụng chưa được Admin duyệt, không thể đăng bài'
            }

        try:
            new_state = not job.website_published
            job.write({'website_published': new_state})
            return {
                'success': True,
                'published': new_state,
                'message': 'Đã đăng tin tuyển dụng' if new_state else 'Đã huỷ xuất bản tin tuyển dụng'
            }
        except Exception as e:
            return {'error': str(e)}

    @http.route('/my/recruitment/job/<int:job_id>/close',
                type='json', auth='user', website=True)
    def close_job(self, job_id, **kwargs):
        job = request.env['hr.job'].sudo().browse(job_id)
        user = request.env.user

        if not job.exists() or job.user_id.id != user.id:
            return {'error': 'Không có quyền thực hiện'}

        if job.website_published:
            return {
                'success': False,
                'error': 'Vui lòng huỷ xuất tin trước khi lưu trữ tin tuyển dụng'
            }

        try:
            job.write({'active': False})
            return {'success': True, 'message': 'Đã lưu trữ tin tuyển dụng'}
        except Exception as e:
            return {'error': str(e)}

    @http.route('/my/recruitment/job/<int:job_id>/reopen',
                type='json', auth='user', website=True)
    def reopen_job(self, job_id, **kwargs):
        job = request.env['hr.job'].sudo().browse(job_id)
        user = request.env.user

        if not job.exists() or job.user_id.id != user.id:
            return {'error': 'Không có quyền thực hiện'}

        try:
            job.write({'active': True})
            return {'success': True, 'message': 'Đã mở lại tin tuyển dụng'}
        except Exception as e:
            return {'error': str(e)}

    @http.route('/my/recruitment/job/create', type='http', auth='user', website=True)
    def portal_create_job(self, **kwargs):
        """Trang tạo tin tuyển dụng mới từ portal"""
        partner = request.env.user.partner_id

        if not partner.is_recruiter:
            return request.redirect('/')

        salary_levels = request.env['hr.recruitment.salary.level'].sudo().search([], order='sequence asc')
        states = request.env['res.country.state'].sudo().search([('country_id.code', '=', 'VN')], order='name asc')


        contract_types = request.env['hr.contract.type'].sudo().search([], order='name asc')

        skills = []
        try:
            skills = request.env['hr.skill'].sudo().search([], order='name asc')
        except Exception:
            pass

        degrees = []
        try:
            degrees = request.env['hr.recruitment.degree'].sudo().search([], order='sequence asc')
        except Exception:
            pass

        values = {
            'salary_levels': salary_levels,
            'states': states,
            'contract_types': contract_types,  # list of (value, label) tuples
            'skills': skills,
            'degrees': degrees,
            'today_str': fields.Date.today().strftime('%Y-%m-%d'),
            'page_name': 'create_job',
        }
        return request.render("eaut_hr_recruitment.portal_create_job", values)

    @http.route('/my/recruitment/job/submit', type='http', auth='user', website=True,
                csrf=False, methods=['POST'])
    def portal_submit_job(self, **post):
        """Xử lý submit form tạo tin tuyển dụng - BÀI SẼ Ở TRẠNG THÁI CHỜ DUYỆT"""
        partner = request.env.user.partner_id
        user = request.env.user

        if not partner.is_recruiter:
            return request.redirect('/')

        name = post.get('name', '').strip()
        description = post.get('description', '')
        salary_level_id = post.get('salary_level_id')
        state_id = post.get('state_id')
        ward_id = post.get('ward_id')
        job_address = post.get('job_address', '').strip()
        no_of_recruitment = post.get('no_of_recruitment', 1)
        skill_ids = request.httprequest.form.getlist('skill_ids')
        contract_type_id = post.get('contract_type_id')
        degree_id = post.get('degree_id')

        # Các trường mới
        requirements = post.get('requirements', '')
        benefits = post.get('benefits', '')
        experience_level = post.get('experience_level', 'mid')
        remote_policy = post.get('remote_policy', 'onsite')
        working_hours = post.get('working_hours', '')
        gender_require = post.get('gender_require', 'both')
        age_require = post.get('age_require', '')
        trial_period = post.get('trial_period', 2)
        application_deadline = post.get('application_deadline') or False

        if not name:
            return request.redirect('/my/recruitment/job/create?error=name_required')

        try:
            import base64
            job_vals = {
                'name': name,
                'is_portal_job': True,
                'description': description,
                'user_id': user.id,
                'recruiter_id': partner.id,
                'no_of_recruitment': int(no_of_recruitment) if no_of_recruitment else 1,
                # Các trường mới
                'requirements': requirements,
                'benefits': benefits,
                'experience_level': experience_level,
                'remote_policy': remote_policy,
                'working_hours': working_hours,
                'gender_require': gender_require,
                'age_require': age_require,
                'trial_period': int(trial_period) if trial_period else 2,
                'application_deadline': application_deadline,
                # QUAN TRỌNG: Set trạng thái chờ duyệt
                'moderation_state': 'approved' if not request.env.user.share else 'pending',
                'website_published': True if not request.env.user.share else False,
            }

            photo_file = request.httprequest.files.get('hr_job_photo')
            if photo_file and photo_file.filename:
                photo_data = base64.b64encode(photo_file.read())
                job_vals['hr_job_photo'] = photo_data

            if salary_level_id:
                job_vals['salary_level_id'] = int(salary_level_id)
            if state_id:
                job_vals['state_id'] = int(state_id)
            if ward_id:
                job_vals['ward_id'] = int(ward_id)
            if job_address:
                job_vals['job_address'] = job_address
            if degree_id:
                job_vals['degree_id'] = int(degree_id)
            if contract_type_id:
                job_vals['contract_type_id'] = int(contract_type_id)

            # Lưu skill_ids để xử lý sau khi tạo job
            selected_skill_ids = []
            if skill_ids:
                selected_skill_ids = [int(s) for s in skill_ids if s.isdigit()]

            job = request.env['hr.job'].sudo().create(job_vals)

            # Tạo job skill records sau khi job đã tồn tại
            if selected_skill_ids:
                SkillType = request.env['hr.skill.type'].sudo()
                JobSkill = request.env['hr.job.skill'].sudo()
                for sid in selected_skill_ids:
                    skill = request.env['hr.skill'].sudo().browse(sid)
                    if skill.exists():
                        # Lấy default skill level cho skill type
                        default_level = SkillType.search([], limit=1)
                        if skill.skill_type_id and skill.skill_type_id.skill_level_ids:
                            default_level = skill.skill_type_id.skill_level_ids.filtered('default_level') or skill.skill_type_id.skill_level_ids[0]
                        JobSkill.create({
                            'job_id': job.id,
                            'skill_id': sid,
                            'skill_type_id': skill.skill_type_id.id,
                            'skill_level_id': default_level.id if default_level else False,
                        })
                _logger.info('Created job %s with skills: %s', job.id, selected_skill_ids)

            _logger.info('Created new job %s by recruiter %s (pending moderation)', job.id, user.id)
            # Chuyển hướng đến trang thông báo chờ duyệt
            return request.redirect('/my/recruitment/job/' + str(job.id) + '/submitted?action=create')

        except Exception as e:
            _logger.error('Error creating job: %s', str(e), exc_info=True)
            import urllib.parse
            return request.redirect('/my/recruitment/job/create?error=' + urllib.parse.quote(str(e)))

    @http.route('/my/recruitment/job/<int:job_id>/submitted', type='http', auth='user', website=True)
    def portal_job_submitted(self, job_id, **kwargs):
        """Trang thông báo sau khi submit thành công - chờ duyệt"""
        partner = request.env.user.partner_id
        user = request.env.user

        if not partner.is_recruiter:
            return request.redirect('/')

        job = request.env['hr.job'].sudo().browse(job_id)
        if not job.exists() or job.user_id.id != user.id:
            return request.redirect('/my/recruitment?tab=jobs')

        # Xác định action type: 'create' hoặc 'edit'
        action_type = kwargs.get('action', 'create')

        values = {
            'job': job,
            'action_type': action_type,
            'page_name': 'job_submitted',
        }
        return request.render("eaut_hr_recruitment.portal_job_submitted", values)

    @http.route('/my/recruitment/job/<int:job_id>/edit', type='http', auth='user', website=True)
    def portal_edit_job(self, job_id, **kwargs):
        """Render trang chỉnh sửa tin tuyển dụng"""
        partner = request.env.user.partner_id
        user = request.env.user

        if not partner.is_recruiter:
            return request.redirect('/')

        # Load job với các fields cần thiết (bao gồm skill_ids)
        job = request.env['hr.job'].sudo().browse(job_id)
        if not job.exists() or job.user_id.id != user.id:
            return request.redirect('/my/recruitment?tab=jobs')

        # Load để trigger computed fields
        job.read(['name', 'description', 'requirements', 'benefits', 'salary_level_id', 'state_id','ward_id',
                  'job_address','contract_type_id', 'degree_id', 'experience_level', 'remote_policy', 'working_hours',
                  'gender_require', 'age_require', 'trial_period', 'application_deadline',
                  'job_skill_ids', 'skill_ids'])

        import json
        salary_levels = request.env['hr.recruitment.salary.level'].sudo().search([], order='sequence asc')
        states = request.env['res.country.state'].sudo().search([('country_id.code', '=', 'VN')], order='name asc')
        wards = request.env['res.ward'].sudo().search(
            [('state_id', '=', job.state_id.id)], order='name asc'
        ) if job.state_id else request.env['res.ward']
        contract_types = request.env['hr.contract.type'].sudo().search([], order='name asc')
        skills = request.env['hr.skill'].sudo().search([], order='name asc')
        degrees = request.env['hr.recruitment.degree'].sudo().search([], order='sequence asc')

        values = {
            'job': job,
            'salary_levels': salary_levels,
             'states': states,
            'wards': wards,
            'contract_types': contract_types,
            'skills': skills,
            'degrees': degrees,
            'today_str': fields.Date.today().strftime('%Y-%m-%d'),

            # Truyền HTML dưới dạng JSON string để nhúng an toàn vào <script>
            'json_description': json.dumps(job.description or ''),
            'json_requirements': json.dumps(job.requirements or ''),
            'json_benefits': json.dumps(job.benefits or ''),
            'page_name': 'edit_job',
        }
        return request.render("eaut_hr_recruitment.portal_edit_job", values)

    @http.route('/my/recruitment/job/<int:job_id>/edit/submit', type='http', auth='user',
                website=True, csrf=False, methods=['POST'])
    def portal_edit_job_submit(self, job_id, **post):
        """Xử lý submit form chỉnh sửa - BÀI SẼ QUAY VỀ TRẠNG THÁI CHỜ DUYỆT"""
        partner = request.env.user.partner_id
        user = request.env.user
        is_portal_user = request.env.user.share

        if not partner.is_recruiter:
            return request.redirect('/')

        job = request.env['hr.job'].sudo().browse(job_id)
        if not job.exists() or job.user_id.id != user.id:
            return request.redirect('/my/recruitment?tab=jobs')

        name = post.get('name', '').strip()
        if not name:
            return request.redirect(f'/my/recruitment/job/{job_id}/edit?error=name_required')

        try:
            import base64
            skill_ids = request.httprequest.form.getlist('skill_ids')
            application_deadline = post.get('application_deadline') or False

            write_vals = {
                'name': name,
                'description': post.get('description', ''),
                'requirements': post.get('requirements', ''),
                'benefits': post.get('benefits', ''),
                'no_of_recruitment': int(post.get('no_of_recruitment', 1) or 1),
                'experience_level': post.get('experience_level', 'mid'),
                'remote_policy': post.get('remote_policy', 'onsite'),
                'working_hours': post.get('working_hours', ''),
                'gender_require': post.get('gender_require', 'both'),
                'age_require': post.get('age_require', ''),
                'trial_period': int(post.get('trial_period', 2) or 2),
                'application_deadline': application_deadline,
                # QUAN TRỌNG: Quay về trạng thái chờ duyệt khi sửa
                # 'moderation_state': 'pending',
                'moderation_state': 'pending' if is_portal_user else job.moderation_state,
            }

            salary_level_id = post.get('salary_level_id')
            state_id = post.get('state_id')
            ward_id = post.get('ward_id')
            job_address = post.get('job_address', '').strip()
            degree_id = post.get('degree_id')
            contract_type_id = post.get('contract_type_id')

            write_vals['salary_level_id'] = int(salary_level_id) if salary_level_id else False
            write_vals['state_id'] = int(state_id) if state_id else False
            write_vals['ward_id'] = int(ward_id) if ward_id else False
            write_vals['job_address'] = job_address if job_address else False
            write_vals['degree_id'] = int(degree_id) if degree_id else False
            write_vals['contract_type_id'] = int(contract_type_id) if contract_type_id else False

            # Xử lý skills - xóa cũ và tạo mới sau khi write
            selected_skill_ids = []
            if skill_ids:
                selected_skill_ids = [int(s) for s in skill_ids if s.isdigit()]
            
            # Xóa skill cũ trước
            job.job_skill_ids.unlink()
            
            # Write các trường khác trước
            job.write(write_vals)
            
            # Xử lý ảnh đại diện
            photo_file = request.httprequest.files.get('hr_job_photo')
            if photo_file and photo_file.filename:
                photo_data = base64.b64encode(photo_file.read())
                job.write({'hr_job_photo': photo_data})


            # Tạo job skill records mới sau khi job đã được write
            if selected_skill_ids:
                SkillType = request.env['hr.skill.type'].sudo()
                JobSkill = request.env['hr.job.skill'].sudo()
                for sid in selected_skill_ids:
                    skill = request.env['hr.skill'].sudo().browse(sid)
                    if skill.exists():
                        default_level = False
                        if skill.skill_type_id and skill.skill_type_id.skill_level_ids:
                            default_level = skill.skill_type_id.skill_level_ids.filtered('default_level') or skill.skill_type_id.skill_level_ids[0]
                        JobSkill.create({
                            'job_id': job.id,
                            'skill_id': sid,
                            'skill_type_id': skill.skill_type_id.id,
                            'skill_level_id': default_level.id if default_level else False,
                        })

            _logger.info('Updated job %s by recruiter %s - set to pending moderation', job.id, user.id)

            # Chuyển hướng đến trang thông báo chờ duyệt (giống khi tạo mới)
            return request.redirect('/my/recruitment/job/' + str(job.id) + '/submitted?action=edit')

        except Exception as e:
            _logger.error('Error updating job %s: %s', job_id, str(e), exc_info=True)
            import urllib.parse
            return request.redirect(f'/my/recruitment/job/{job_id}/edit?error=' + urllib.parse.quote(str(e)))


    # ============ API danh sách tỉnh/thành ============
    @http.route('/hr_recruitment/api/states', type='json', auth='public', website=True)
    def api_get_states(self):
        states = request.env['res.country.state'].sudo().search_read(
            [('country_id.code', '=', 'VN')],
            ['id', 'name'],
            order='name'
        )
        return {'states': states}
    # ============ API tạo nhanh ============
    @http.route('/my/recruitment/api/create/salary_level', type='json', auth='user', website=True)
    def api_create_salary_level(self, **kwargs):
        partner = request.env.user.partner_id
        if not partner.is_recruiter:
            return {'error': 'Không có quyền'}

        name = kwargs.get('name', '').strip()
        min_salary = kwargs.get('min_salary', 0)
        max_salary = kwargs.get('max_salary', 0)

        if not name:
            return {'error': 'Tên mức lương không được trống'}

        try:
            level = request.env['hr.recruitment.salary.level'].sudo().create({
                'name': name,
                'min_salary': int(min_salary) if min_salary else 0,
                'max_salary': int(max_salary) if max_salary else 0,
            })
            return {'success': True, 'id': level.id, 'name': level.display_name}
        except Exception as e:
            return {'error': str(e)}

    @http.route('/my/recruitment/api/create/degree', type='json', auth='user', website=True)
    def api_create_degree(self, **kwargs):
        partner = request.env.user.partner_id
        if not partner.is_recruiter:
            return {'error': 'Không có quyền'}

        name = kwargs.get('name', '').strip()
        if not name:
            return {'error': 'Tên bằng cấp không được trống'}

        try:
            if 'hr.recruitment.degree' not in request.env:
                return {'error': 'Model không tồn tại'}
            degree = request.env['hr.recruitment.degree'].sudo().create({'name': name})
            return {'success': True, 'id': degree.id, 'name': degree.name}
        except Exception as e:
            return {'error': str(e)}

    @http.route('/my/recruitment/api/create/skill', type='json', auth='user', website=True)
    def api_create_skill(self, **kwargs):
        partner = request.env.user.partner_id
        if not partner.is_recruiter:
            return {'error': 'Khong co quyen'}

        name = kwargs.get('name', '').strip()
        skill_type_id = kwargs.get('skill_type_id')
        if not name:
            return {'error': 'Ten ky nang khong duoc trong'}
        if not skill_type_id:
            return {'error': 'Vui long chon loai ky nang'}

        try:
            if 'hr.skill' not in request.env:
                return {'error': 'Model khong ton tai'}
            skill = request.env['hr.skill'].sudo().create({
                'name': name,
                'skill_type_id': int(skill_type_id),
            })
            return {'success': True, 'id': skill.id, 'name': skill.name}
        except Exception as e:
            return {'error': str(e)}

    @http.route('/my/recruitment/api/skill_types', type='json', auth='user', website=True)
    def api_get_skill_types(self, **kwargs):
        types = request.env['hr.skill.type'].sudo().search([], order='name asc')
        return [{'id': t.id, 'name': t.name} for t in types]

    # ============ TRANG CHI TIẾT JOB CÔNG KHAI ============

    @http.route([
        '/recruitment/detail/<int:job_id>',
    ], type='http', auth='public', website=True, priority=5)
    def job_detail_public(self, job_id=None, **kwargs):

        job = request.env['hr.job'].sudo().browse(job_id)

        if not job or not job.exists():
            return request.redirect('/jobs')
        
        # Lấy thông tin công ty
        company = job.company_id or request.env.company
        partner = job.user_id.partner_id if job.user_id else company.partner_id
        # _logger.info('Partner fields: %s', partner.read()[0])
        # Định dạng lương
        salary_display = ''
        if job.salary_level_id:
            level = job.salary_level_id
            if level.min_salary and level.max_salary:
                salary_display = f"{level.min_salary:,.0f} - {level.max_salary:,.0f} VNĐ"
            elif level.name:
                salary_display = level.name
        
        # Format kinh nghiệm
        experience_labels = {
            'intern': 'Thực tập',
            'fresher': 'Mới tốt nghiệp',
            'junior': 'Junior (1-2 năm)',
            'mid': 'Mid-level (3-5 năm)',
            'senior': 'Senior (5+ năm)',
            'lead': 'Lead / Quản lý',
        }
        remote_labels = {
            'onsite': 'Tại văn phòng',
            'hybrid': 'Hybrid',
            'remote': 'Remote',
        }
        
        values = {
            'job': job,
            'company': company,
            'partner': partner,
            'salary_display': salary_display,
            'experience_label': experience_labels.get(job.experience_level, ''),
            'remote_label': remote_labels.get(job.remote_policy, ''),
            'page_name': 'job_detail',
        }
        return request.render("eaut_hr_recruitment.job_detail_public", values)

    # Xuất ex by Dung
# ============ XUẤT EXCEL TIN TUYỂN DỤNG ============
    @http.route('/my/recruitment/export/jobs', type='http', auth='user', website=True)
    def export_jobs_excel(self, **kwargs):
        partner = request.env.user.partner_id
        user = request.env.user

        if not partner.is_recruiter:
            return request.redirect('/')

        jobs = request.env['hr.job'].sudo().search(
            [('user_id', '=', user.id)], order='id desc'
        )

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Tin tuyển dụng')

        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#1E3769', 'font_color': '#FFFFFF',
            'border': 1, 'align': 'center', 'valign': 'vcenter',
        })
        cell_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter'})
        date_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter', 'num_format': 'dd/mm/yyyy'})

        headers = [
             'Vị trí', 'Trạng thái duyệt', 'Đã xuất bản', 'Tỉnh/Thành phố',
            'Phường/Xã', 'Địa chỉ chi tiết', 'Mức lương', 'Loại công việc',
            'Trình độ yêu cầu', 'Số lượng tuyển', 'Hạn nộp hồ sơ',
            'Số ứng viên', 'Mô tả công việc', 'Yêu cầu ứng viên',
            'Quyền lợi', 'Ngày tạo',
        ]
        for col, title in enumerate(headers):
            sheet.write(0, col, title, header_fmt)

        moderation_labels = {
            'pending': 'Chờ duyệt', 'approved': 'Đã duyệt', 'rejected': 'Từ chối',
        }

        row = 1
        for job in jobs:
            applicant_count = request.env['hr.applicant'].sudo().search_count(
                [('job_id', '=', job.id)]
            )
            sheet.write(row, 0, job.name or '', cell_fmt)
            sheet.write(row, 1, moderation_labels.get(job.moderation_state, ''), cell_fmt)
            sheet.write(row, 2, 'Có' if job.website_published else 'Không', cell_fmt)
            sheet.write(row, 3, job.state_id.name if job.state_id else '', cell_fmt)
            sheet.write(row, 4, job.ward_id.name if job.ward_id else '', cell_fmt)
            sheet.write(row, 5, job.job_address or '', cell_fmt)
            sheet.write(row, 6, job.salary_level_id.name if job.salary_level_id else '', cell_fmt)
            sheet.write(row, 7, job.contract_type_id.name if job.contract_type_id else '', cell_fmt)
            sheet.write(row, 8, job.degree_id.name if job.degree_id else '', cell_fmt)
            sheet.write(row, 9, job.no_of_recruitment or 0, cell_fmt)
            if job.application_deadline:
                sheet.write_datetime(row, 10, job.application_deadline, date_fmt)
            else:
                sheet.write(row, 10, 'Không thời hạn', cell_fmt)
            sheet.write(row, 11, applicant_count, cell_fmt)
            # Strip HTML tags cho mô tả, yêu cầu, quyền lợi
            sheet.write(row, 12,html2plaintext(job.description) or '', cell_fmt)
            sheet.write(row, 13, html2plaintext(job.requirements) or '', cell_fmt)
            sheet.write(row, 14, html2plaintext(job.benefits) or '', cell_fmt)
            if job.create_date:
                sheet.write_datetime(row, 15, job.create_date, date_fmt)
            else:
                sheet.write(row, 15, '', cell_fmt)
            row += 1

        for col, width in enumerate([
            28, 14, 12, 16, 16, 30, 18, 16, 16, 12,
            14, 12, 30, 30, 30, 14
        ]):
            sheet.set_column(col, col, width)

        workbook.close()
        output.seek(0)
        file_data = output.read()
        output.close()

        return request.make_response(
            file_data,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', 'attachment; filename="tin_tuyen_dung.xlsx"'),
            ]
        )

    # ============ XUẤT EXCEL ỨNG VIÊN ============
    @http.route('/my/recruitment/export/applicants', type='http', auth='user', website=True)
    def export_applicants_excel(self, **kwargs):
        partner = request.env.user.partner_id
        user = request.env.user

        if not partner.is_recruiter:
            return request.redirect('/')

        job_ids = request.env['hr.job'].sudo().search(
            [('user_id', '=', user.id)]
        ).ids
        applicants = request.env['hr.applicant'].sudo().search(
            [('job_id', 'in', job_ids)], order='id desc'
        ) if job_ids else request.env['hr.applicant']

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Ứng viên')

        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#1E3769', 'font_color': '#FFFFFF',
            'border': 1, 'align': 'center', 'valign': 'vcenter',
        })
        cell_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter'})
        date_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter', 'num_format': 'dd/mm/yyyy'})

        headers = [
            'Ứng viên', 'Vị trí ứng tuyển', 'Email', 'Số điện thoại','Giới thiệu ngắn của ứng viên','CV đính kèm',
            'Kết quả xét duyệt', 'Ngày phỏng vấn', 'Ghi chú nhà tuyển dụng', 'Ngày nộp',
        ]
        for col, title in enumerate(headers):
            sheet.write(0, col, title, header_fmt)

        feedback_labels = {
            'pending': 'Chờ xét duyệt', 'interview': 'Mời phỏng vấn',
            'approved': 'Đạt yêu cầu', 'contracted': 'Hợp đồng ký', 'rejected': 'Fail',
        }

        row = 1
        for applicant in applicants:
            sheet.write(row, 0, applicant.partner_name or applicant.name or '', cell_fmt)
            sheet.write(row, 1, applicant.job_id.name if applicant.job_id else '', cell_fmt)
            sheet.write(row, 2, applicant.email_from or '', cell_fmt)
            sheet.write(row, 3, applicant.partner_phone or '', cell_fmt)
            intro_text = ''
            if applicant.short_intro_candidate:
                import re
                intro_text = re.sub('<[^<]+?>', '', applicant.short_intro_candidate).strip()
            sheet.write(row, 4, intro_text, cell_fmt)

            cv_names = ', '.join(applicant.attachment_ids.mapped('name')) if applicant.attachment_ids else ''
            sheet.write(row, 5, cv_names, cell_fmt)

            sheet.write(row, 6, feedback_labels.get(applicant.recruiter_feedback, ''), cell_fmt)

            if applicant.interview_date:
                sheet.write_datetime(row, 7, applicant.interview_date, date_fmt)
            else:
                sheet.write(row, 7, '', cell_fmt)

            sheet.write(row, 8, applicant.recruiter_note or '', cell_fmt)

            if applicant.create_date:
                sheet.write_datetime(row, 9, applicant.create_date, date_fmt)
            else:
                sheet.write(row, 9, '', cell_fmt)

            row += 1

        for col, width in enumerate([24, 24, 26, 16, 30, 30, 18, 18, 30, 20]):
            sheet.set_column(col, col, width)

        workbook.close()
        output.seek(0)
        file_data = output.read()
        output.close()

        return request.make_response(
            file_data,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', 'attachment; filename="ung_vien.xlsx"'),
            ]
        )