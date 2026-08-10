from unittest.mock import patch
from odoo import http
from odoo.http import request
from odoo.addons.website_hr_recruitment.controllers.main import WebsiteHrRecruitment

SORT_OPTIONS = {
    'name_asc': 'name asc',
    'name_desc': 'name desc',
    'date_desc': 'create_date desc',
    'date_asc': 'create_date asc',
}


class WebsiteHrRecruitmentSalary(WebsiteHrRecruitment):

    @http.route()
    def jobs(self, page=1, salary_level_id=None, state_id=None, ward_id=None, sort=None, **kwargs):
        salary_level = self._get_record_safe('hr.recruitment.salary.level', salary_level_id)
        state = self._get_record_safe('res.country.state', state_id)
        ward = None
        if ward_id:
            ward_rec = self._get_record_safe('res.ward', ward_id)
            if ward_rec and (not state or ward_rec.state_id.id == state.id):
                ward = ward_rec

        custom_order = SORT_OPTIONS.get(sort) if sort else None
        website_class = type(request.website)
        original_search = website_class._search_with_fuzzy

        def patched_search(self_website, search_type, search, limit, order, options):
            base_order = custom_order if custom_order else (order or 'id desc')
            final_order = f'is_pinned desc, {base_order}'
            total, details, fuzzy = original_search(self_website, search_type, search, limit, final_order, options)
            if details and details[0].get('results'):
                results = details[0]['results']
                if salary_level:
                    results = results.filtered(lambda j: j.salary_level_id.id == salary_level.id)
                if state:
                    results = results.filtered(lambda j: j.state_id.id == state.id)
                if ward:
                    results = results.filtered(lambda j: j.ward_id.id == ward.id)
                details[0]['results'] = results
                total = len(results)
            return total, details, fuzzy

        # Luôn patch, không còn nhánh early-return bỏ qua patch nữa
        with patch.object(website_class, '_search_with_fuzzy', patched_search):
            response = super().jobs(page=page, **kwargs)

        if hasattr(response, 'qcontext'):
            response.qcontext.update({
                'salary_level_id': salary_level,
                'state_id': state,
                'ward_id': ward,
                'sort_param': sort,
            })
        return response

    # lấy record không tồn tại thì coi như không có, ko crash trang.
    @staticmethod
    def _get_record_safe(model, rec_id):
        if not rec_id:
            return None
        try:
            rec = request.env[model].sudo().browse(int(rec_id))
            return rec if rec.exists() else None
        except Exception:
            return None

    @http.route('/hr_recruitment/api/wards', type='http', auth='public', website=True, csrf=False)
    def api_get_wards(self, state_id=None, **kwargs):
        import json
        wards = []
        if state_id:
            try:
                wards = request.env['res.ward'].sudo().search(
                    [('state_id', '=', int(state_id))], order='name'
                )
            except Exception:
                wards = []
        data = {'wards': [{'id': w.id, 'name': w.name} for w in wards]}
        return request.make_response(
            json.dumps(data),
            headers=[('Content-Type', 'application/json')]
        )