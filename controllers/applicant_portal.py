# -*- coding: utf-8 -*-
import logging, json
from markupsafe import Markup
from odoo.http import request, route
from odoo.addons.portal.controllers.portal import CustomerPortal

_logger = logging.getLogger(__name__)
FEEDBACK_TO_KANBAN = {
        'pending': 'normal',
        'interview': 'done',
        'approved': 'done',
        'contracted': 'done',
        'rejected': 'blocked',
    }

class ApplicantPortal(CustomerPortal):


    def _get_applicant_domain(self):
        """Lấy domain để lọc ứng viên thuộc jobs của recruiter hiện tại"""
        user = request.env.user
        return [
            ('job_id.user_id', '=', user.id)
        ]

    # @route('/my/recruitment/applicant/<int:applicant_id>',
    #        type='http', auth='user', website=True)
    # def portal_applicant_detail(self, applicant_id, **kwargs):
    #     """Trang chi tiết ứng viên"""
    #     applicant = request.env['hr.applicant'].sudo().browse(applicant_id)
    #
    #     if not applicant.exists():
    #         return request.redirect('/my/recruitment?tab=applicants')
    #
    #     # Kiểm tra quyền: chỉ recruiter sở hữu job mới được xem
    #     user = request.env.user
    #     if applicant.job_id.user_id.id != user.id:
    #         _logger.warning('User %s attempted to access applicant %s without permission',
    #                       user.id, applicant_id)
    #         return request.redirect('/my/recruitment?tab=applicants')
    #
    #     # Lấy danh sách stages để hiển thị (tất cả stages)
    #     stages = request.env['hr.recruitment.stage'].sudo().search([], order='sequence asc')
    #
    #     values = {
    #         'applicant': applicant,
    #         'stages': stages,
    #         'page_name': 'applicant_detail',
    #         'redirect_url': '/my/recruitment?tab=applicants',
    #     }
    #
    #     return request.render('hr_recruitment_pro.portal_applicant_detail', values)

    @route('/my/recruitment/applicant/<int:applicant_id>/action',
           type='json', auth='user', website=True)
    def portal_applicant_action(self, applicant_id, action, **kwargs):
        """Xử lý chuyển trạng thái - không cần note"""
        applicant = request.env['hr.applicant'].sudo().browse(applicant_id)

        if not applicant.exists():
            return {'error': 'Applicant not found'}

        user = request.env.user
        if applicant.job_id.user_id.id != user.id:
            return {'error': 'Permission denied'}

        VALID_ACTIONS = {
            'pending': ('pending', 'Chuyển về Chờ xét duyệt'),
            'interview': ('interview', 'Đã chuyển sang Mời phỏng vấn'),
            'approved': ('approved', 'Đã đánh dấu Đạt yêu cầu'),
            'contracted': ('contracted', 'Đã xác nhận Hợp đồng ký'),
            'rejected': ('rejected', 'Đã đánh dấu Fail'),
        }

        if action not in VALID_ACTIONS:
            return {'error': f'Unknown action: {action}'}

        try:
            feedback_value, message = VALID_ACTIONS[action]
            applicant.write({
                'recruiter_feedback': feedback_value,
                'kanban_state': FEEDBACK_TO_KANBAN.get(feedback_value, 'normal'),
            })
            _logger.info('Applicant %s → %s by user %s', applicant_id, feedback_value, user.id)
            return {'success': True, 'message': message}

        except Exception as e:
            _logger.error('Error processing applicant action: %s', str(e))
            return {'error': str(e)}

    @route('/my/recruitment/applicant/<int:applicant_id>/update_note',
           type='http', auth='user', website=True, csrf=True)
    def portal_update_note(self, applicant_id, **post):
        """Cập nhật ghi chú nhà tuyển dụng"""
        _logger.info('===== START: portal_update_note =====')
        _logger.info('applicant_id: %s', applicant_id)
        _logger.info('POST data: %s', post)
        _logger.info('User: %s (id=%s)', request.env.user.name, request.env.user.id)

        applicant = request.env['hr.applicant'].sudo().browse(applicant_id)

        if not applicant.exists():
            _logger.warning('Applicant %s does not exist', applicant_id)
            return request.redirect('/my/recruitment?tab=applicants')

        user = request.env.user
        if applicant.job_id.user_id.id != user.id:
            _logger.warning('User %s has no permission to update applicant %s', user.id, applicant_id)
            return request.redirect('/my/recruitment?tab=applicants')

        note = post.get('note', '')
        _logger.info('Note content length: %s', len(note))
        _logger.info('Note preview (first 100 chars): %s', note[:100] if note else 'EMPTY')

        try:
            applicant.write({'recruiter_note': note})
            _logger.info('SUCCESS: Updated recruiter_note for applicant %s', applicant_id)
            _logger.info('Verify - New note in DB: %s', applicant.recruiter_note[:100] if applicant.recruiter_note else 'EMPTY')
        except Exception as e:
            _logger.error('ERROR updating note for applicant %s: %s', applicant_id, str(e), exc_info=True)

        _logger.info('===== END: portal_update_note =====')
        return request.redirect(f'/my/recruitment/applicant/{applicant_id}')

    @route('/my/recruitment/applicant/<int:applicant_id>/schedule_interview',
           type='http', auth='user', website=True, csrf=True)
    def portal_schedule_interview(self, applicant_id, **post):
        """Hẹn lịch phỏng vấn"""
        applicant = request.env['hr.applicant'].sudo().browse(applicant_id)

        if not applicant.exists():
            return request.redirect('/my/recruitment?tab=applicants')

        user = request.env.user
        if applicant.job_id.user_id.id != user.id:
            return request.redirect('/my/recruitment?tab=applicants')

        interview_date = post.get('interview_date')
        interview_note = post.get('interview_note', '')

        if interview_date:
            applicant.write({
                'interview_date': interview_date,
                'interview_note': interview_note,
                # KHÔNG đổi stage_id, KHÔNG đổi recruiter_feedback
            })

        return request.redirect(f'/my/recruitment/applicant/{applicant_id}')

    @route('/my/recruitment/applicant/<int:applicant_id>',
           type='http', auth='user', website=True)
    def portal_applicant_detail(self, applicant_id, **kwargs):
        applicant = request.env['hr.applicant'].sudo().browse(applicant_id)

        if not applicant.exists():
            return request.redirect('/my/recruitment?tab=applicants')

        user = request.env.user
        if applicant.job_id.user_id.id != user.id:
            return request.redirect('/my/recruitment?tab=applicants')

        stages = request.env['hr.recruitment.stage'].sudo().search([], order='sequence asc')

        # Parse email log
        try:
            email_log = json.loads(applicant.interview_email_log or '[]')
        except Exception:
            email_log = []

        values = {
            'applicant': applicant,
            'stages': stages,
            'page_name': 'applicant_detail',
            'redirect_url': '/my/recruitment?tab=applicants',
            'interview_email_log': email_log,  # <-- thêm dòng này
            'msg': kwargs.get('msg', ''),  # <-- thêm dòng này
        }

        return request.render('hr_recruitment_pro.portal_applicant_detail', values)

    @route('/my/recruitment/applicant/<int:applicant_id>/send_interview_email',
           type='http', auth='user', website=True, csrf=True)
    def portal_send_interview_email(self, applicant_id, **post):
        """Gửi email mời phỏng vấn cho ứng viên"""
        applicant = request.env['hr.applicant'].sudo().browse(applicant_id)

        if not applicant.exists():
            return request.redirect('/my/recruitment?tab=applicants')

        user = request.env.user
        if applicant.job_id.user_id.id != user.id:
            return request.redirect('/my/recruitment?tab=applicants')

        interview_date_str = post.get('interview_date', '')
        location = post.get('location', '').strip()
        format_type = post.get('format_type', '').strip()
        extra_note = post.get('extra_note', '').strip()

        if not interview_date_str:
            return request.redirect(f'/my/recruitment/applicant/{applicant_id}?msg=no_date#interview-tab')

        from datetime import datetime
        try:
            interview_dt = datetime.strptime(interview_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            return request.redirect(f'/my/recruitment/applicant/{applicant_id}?msg=invalid_date#interview-tab')

        # Lưu interview_date vào record
        applicant.write({'interview_date': interview_dt})

        # Build nội dung email
        candidate_name = applicant.partner_name or applicant.name or 'Ứng viên'
        job_name = applicant.job_id.name or ''
        company_name = request.env.company.name
        recruiter_name = user.name
        location_display = location or format_type or 'Sẽ thông báo sau'

        extra_html = f'<p style="color:#555;font-style:italic;">{extra_note}</p>' if extra_note else ''

        body_html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;border:1px solid #e0e0e0;border-radius:8px;overflow:hidden;">
            <div style="background:#1E3769;padding:24px;text-align:center;">
                <h2 style="color:#1E3769;margin:0;font-size:20px;">THƯ MỜI PHỎNG VẤN</h2>
                
            </div>
            <div style="padding:28px;background:#ffffff;">
                <p>Kính gửi <strong>{candidate_name}</strong>,</p>
                <p>Chúng tôi trân trọng thông báo bạn đã vượt qua vòng xét hồ sơ
                   cho vị trí <strong>{job_name}</strong>.</p>
                <p>Chúng tôi xin mời bạn tham dự buổi phỏng vấn theo thông tin sau:</p>

              <table style="width:100%;border-collapse:collapse;margin:16px 0;">
    <tr>
        <td style="padding:12px 16px;font-weight:bold;width:40%;background-color:#1E3769;color:#ffffff;">
            Thời gian
        </td>
        <td style="padding:12px 16px;background-color:#1E3769;color:#ffffff;">
            {interview_dt.strftime('%H:%M - %d/%m/%Y')}
        </td>
    </tr>
    <tr>
        <td style="padding:12px 16px;font-weight:bold;background-color:#f8fafc;color:#1E3769;border-top:2px solid #1E3769;">
          Địa điểm
        </td>
        <td style="padding:12px 16px;background-color:#f8fafc;color:#333333;border-top:2px solid #1E3769;">
            {location_display}
        </td>
    </tr>
</table>

                {extra_html}
                <p>Vui lòng xác nhận tham dự bằng cách phản hồi email này trước ngày phỏng vấn.</p>
                <p style="margin-top:32px;">Trân trọng,<br/>
                   <strong>{recruiter_name}</strong><br/>
                   
                </p>
            </div>
            <div style="background:#f1f5f9;padding:12px;text-align:center;">
                <small style="color:#94a3b8;">Email này được gửi tự động từ hệ thống tuyển dụng.</small>
            </div>
        </div>
        """

        # Gửi qua Odoo mail
        try:
            partner_ids = [applicant.partner_id.id] if applicant.partner_id else []
            applicant.sudo().message_post(
                body=Markup(body_html),  # ← chỉ thêm Markup() ở đây
                subject=f"[{company_name}] Thư mời phỏng vấn - {job_name}",
                message_type='email',
                subtype_xmlid='mail.mt_comment',
                partner_ids=partner_ids,
                email_from=user.email_formatted,
            )
            _logger.info('Interview email sent for applicant %s by user %s', applicant_id, user.id)
        except Exception as e:
            _logger.error('Failed to send interview email: %s', str(e), exc_info=True)
            return request.redirect(f'/my/recruitment/applicant/{applicant_id}?msg=error#interview-tab')

        # Append vào email log
        import json
        from datetime import datetime as dt
        try:
            log = json.loads(applicant.interview_email_log or '[]')
        except Exception:
            log = []

        log.insert(0, {
            'sent_at': dt.now().strftime('%H:%M %d/%m/%Y'),
            'sent_by': user.name,
            'interview_date': interview_dt.strftime('%H:%M - %d/%m/%Y'),
            'location': location_display,
            'format_type': format_type,
        })
        applicant.write({'interview_email_log': json.dumps(log, ensure_ascii=False)})

        return request.redirect(f'/my/recruitment/applicant/{applicant_id}?msg=sent#interview-tab')