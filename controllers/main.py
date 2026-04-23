# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.website_hr_recruitment.controllers.main import WebsiteHrRecruitment


class WebsiteHrRecruitmentSalary(WebsiteHrRecruitment):

    @http.route()
    def jobs(self, **kwargs):
        # Lấy tham số salary_level_id từ URL
        salary_level_id = kwargs.get('salary_level_id')
        salary_level = None

        if salary_level_id:
            salary_level = request.env['hr.recruitment.salary.level'].sudo().browse(int(salary_level_id))
            if not salary_level.exists():
                salary_level = None

        # Gọi method gốc để lấy response
        response = super().jobs(**kwargs)

        if hasattr(response, 'qcontext'):
            qcontext = response.qcontext

            # Lọc jobs theo salary level nếu có
            if salary_level and 'jobs' in qcontext:
                jobs = qcontext['jobs']
                jobs = jobs.filtered(
                    lambda j: j.salary_level_id and j.salary_level_id.id == salary_level.id
                )
                qcontext['jobs'] = jobs

            qcontext['salary_level_id'] = salary_level

        return response