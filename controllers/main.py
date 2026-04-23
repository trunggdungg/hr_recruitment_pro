from unittest.mock import patch
from odoo import http
from odoo.http import request
from odoo.addons.website_hr_recruitment.controllers.main import WebsiteHrRecruitment


class WebsiteHrRecruitmentSalary(WebsiteHrRecruitment):

    @http.route()
    def jobs(self, page=1, salary_level_id=None, location_id=None, **kwargs):
        salary_level = None
        location = None

        # Lấy salary_level
        if salary_level_id:
            try:
                level = request.env['hr.recruitment.salary.level'].sudo().browse(int(salary_level_id))
                if level.exists():
                    salary_level = level
            except Exception:
                pass

        # Lấy location
        if location_id:
            try:
                loc = request.env['hr.recruitment.location'].sudo().browse(int(location_id))
                if loc.exists():
                    location = loc
            except Exception:
                pass

        # Nếu không có filter nào → gọi super bình thường
        if not salary_level and not location:
            response = super().jobs(page=page, **kwargs)
            if hasattr(response, 'qcontext'):
                response.qcontext['salary_level_id'] = None
                response.qcontext['location_id'] = None
            return response

        # Lấy class thực của website object để patch đúng chỗ
        website_class = type(request.website)
        original_search = website_class._search_with_fuzzy
        _salary_level = salary_level
        _location = location

        def patched_search(self_website, search_type, search, limit, order, options):
            total, details, fuzzy = original_search(self_website, search_type, search, limit, order, options)
            if details and details[0].get('results'):
                results = details[0]['results']
                if _salary_level and _location:
                    # Cả 2 filter
                    filtered = results.filtered(
                        lambda j: j.salary_level_id and j.salary_level_id.id == _salary_level.id
                                  and j.location_id and j.location_id.id == _location.id
                    )
                elif _salary_level:
                    # Chỉ salary
                    filtered = results.filtered(
                        lambda j: j.salary_level_id and j.salary_level_id.id == _salary_level.id
                    )
                else:
                    # Chỉ location
                    filtered = results.filtered(
                        lambda j: j.location_id and j.location_id.id == _location.id
                    )
                details[0]['results'] = filtered
                total = len(filtered)
            return total, details, fuzzy

        with patch.object(website_class, '_search_with_fuzzy', patched_search):
            response = super().jobs(page=page, **kwargs)

        if hasattr(response, 'qcontext'):
            response.qcontext['salary_level_id'] = salary_level
            response.qcontext['location_id'] = location

        return response
