# -*- coding: utf-8 -*-
import logging
from odoo import http,fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

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

        # Domain tìm kiếm
        domain = [('user_id', '=', user.id)]
        if search_query:
            domain += [('name', 'ilike', search_query)]

        total_jobs = request.env['hr.job'].sudo().search_count(domain)
        offset = (page - 1) * per_page
        total_pages = max(1, (total_jobs + per_page - 1) // per_page)

        jobs = request.env['hr.job'].sudo().search(
            domain, limit=per_page, offset=offset, order='id desc'
        )

        applicant_counts = {}
        for job in jobs:
            applicant_counts[job.id] = request.env['hr.applicant'].sudo().search_count([
                ('job_id', '=', job.id)
            ])

            # Đếm TOÀN BỘ applicants của recruiter không phụ thuộc vào trang
        all_job_ids = request.env['hr.job'].sudo().search(
            [('user_id', '=', user.id)]  # Không dùng search_query ở đây
        ).ids

        # Tất cả applicants để hiển thị ở tab Ứng viên
        all_applicants = request.env['hr.applicant'].sudo().search([
            ('job_id', 'in', all_job_ids)
        ]) if all_job_ids else request.env['hr.applicant']

        total_applicants_count = request.env['hr.applicant'].sudo().search_count([
            ('job_id', 'in', all_job_ids)
        ]) if all_job_ids else 0
        total_applicants_counts = len(all_applicants)
        job_ids = jobs.ids
        applicants = request.env['hr.applicant'].sudo().search([
            ('job_id', 'in', job_ids)
        ]) if job_ids else request.env['hr.applicant']

        values = {
            'partner': partner,
            'jobs': jobs,
            'applicant_counts': applicant_counts,
            'jobs_count': total_jobs,
            'applicants': all_applicants,
            'applicants_count': total_applicants_counts,
            'active_tab': active_tab,
            'page_name': 'recruitment',
            # search + paging
            'search_query': search_query,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'total_jobs': total_jobs,
        }
        return request.render("hr_recruitment_pro.portal_my_recruitment", values)

    # @http.route('/my/recruitment/job/<int:job_id>/toggle_publish',
    #             type='json', auth='user', website=True)
    # def toggle_job_publish(self, job_id, **kwargs):
    #     job = request.env['hr.job'].sudo().browse(job_id)
    #     user = request.env.user
    #
    #     if not job.exists() or job.user_id.id != user.id:
    #         return {'error': 'Không có quyền thực hiện'}
    #
    #     try:
    #         new_state = not job.website_published
    #         job.write({'website_published': new_state})
    #         return {
    #             'success': True,
    #             'published': new_state,
    #             'message': 'Đã đăng tin tuyển dụng' if new_state else 'Đã huỷ xuất bản tin tuyển dụng'
    #         }
    #     except Exception as e:
    #         return {'error': str(e)}
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
        locations = request.env['hr.recruitment.location'].sudo().search([], order='name asc')

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
            'locations': locations,
            'contract_types': contract_types,  # list of (value, label) tuples
            'skills': skills,
            'degrees': degrees,
            'today_str': fields.Date.today().strftime('%Y-%m-%d'),
            'page_name': 'create_job',
        }
        return request.render("hr_recruitment_pro.portal_create_job", values)

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
        location_id = post.get('location_id')
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

            if salary_level_id:
                job_vals['salary_level_id'] = int(salary_level_id)
            if location_id:
                job_vals['location_id'] = int(location_id)
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
        return request.render("hr_recruitment_pro.portal_job_submitted", values)

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
        job.read(['name', 'description', 'requirements', 'benefits', 'salary_level_id', 'location_id',
                  'contract_type_id', 'degree_id', 'experience_level', 'remote_policy', 'working_hours',
                  'gender_require', 'age_require', 'trial_period', 'application_deadline',
                  'job_skill_ids', 'skill_ids'])

        import json
        salary_levels = request.env['hr.recruitment.salary.level'].sudo().search([], order='sequence asc')
        locations = request.env['hr.recruitment.location'].sudo().search([], order='name asc')
        contract_types = request.env['hr.contract.type'].sudo().search([], order='name asc')
        skills = request.env['hr.skill'].sudo().search([], order='name asc')
        degrees = request.env['hr.recruitment.degree'].sudo().search([], order='sequence asc')

        values = {
            'job': job,
            'salary_levels': salary_levels,
            'locations': locations,
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
        return request.render("hr_recruitment_pro.portal_edit_job", values)

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
                #'moderation_state': 'pending',
                'moderation_state': 'pending' if is_portal_user else job.moderation_state,
            }

            salary_level_id = post.get('salary_level_id')
            location_id = post.get('location_id')
            degree_id = post.get('degree_id')
            contract_type_id = post.get('contract_type_id')

            write_vals['salary_level_id'] = int(salary_level_id) if salary_level_id else False
            write_vals['location_id'] = int(location_id) if location_id else False
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

    @http.route('/my/recruitment/api/create/location', type='json', auth='user', website=True)
    def api_create_location(self, **kwargs):
        partner = request.env.user.partner_id
        if not partner.is_recruiter:
            return {'error': 'Không có quyền'}

        name = kwargs.get('name', '').strip()
        city = kwargs.get('city', '').strip()

        if not name or not city:
            return {'error': 'Tên và thành phố không được trống'}

        try:
            # Kiểm tra city trùng trước (do constraint unique(city))
            existing = request.env['hr.recruitment.location'].sudo().search(
                [('city', '=', city)], limit=1
            )
            if existing:
                return {'error': f'Thành phố "{city}" đã tồn tại (địa điểm: {existing.display_name})'}

            location = request.env['hr.recruitment.location'].sudo().create({
                'name': name,
                'city': city,
            })
            return {'success': True, 'id': location.id, 'name': location.display_name}
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
        partner = request.env.user.partner_id
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
        return request.render("hr_recruitment_pro.job_detail_public", values)

