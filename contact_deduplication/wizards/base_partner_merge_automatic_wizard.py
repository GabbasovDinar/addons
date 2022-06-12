import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

try:
    from thefuzz import fuzz
except ImportError:
    fuzz = None
    _logger.warning("Not found \"thefuzz\" python lib. Please use \"pip install thefuzz\" ")


class BasePartnerMergeAutomaticWizard(models.TransientModel):
    _inherit = "base.partner.merge.automatic.wizard"

    @api.onchange("dst_partner_id")
    def _onchange_dst_partner_id(self):
        """
        Recompute `similarity_threshold` field after change destination partner
        """
        if self.group_by_similar_name:
            for partner in self.partner_ids:
                partner.similarity_threshold = fuzz.ratio(self.dst_partner_id.name, partner.name)

    @api.constrains("similarity_threshold", "group_by_similar_name")
    def _check_similarity_threshold(self):
        """
        Check that `similarity_threshold` has values in the range from 0 to 100
        """
        if (
            self.group_by_similar_name and
            (self.similarity_threshold < 0 or self.similarity_threshold > 100)
        ):
            raise ValidationError(_("The entered value of \"Similarity Threshold\" must be between 0 and 100."))

    @api.constrains("merge_limit")
    def _check_merge_limit(self):
        """
        Check that `merge_limit` has values more or equal to 0
        """
        if self.merge_limit < 0:
            raise ValidationError(_("The entered value of \"Merge Limit\" must not be negative."))

    group_by_without_parent_id = fields.Boolean(
        string="Without Parent Company",
        help="Search partners without a parent.",
    )
    group_by_similar_name = fields.Boolean(
        string="With Similar Name",
        help="Search for partners with a similar name.",
    )
    similarity_threshold = fields.Integer(
        string="Similarity Threshold",
        default=50,
        help="Search for partners without a parent and with a similar name "
             "whose similarity threshold is greater than the specified value. "
             "Values must be between 0 and 100",
    )
    merge_limit = fields.Integer(
        default=3,
        help="0 - for unlimited merge",
    )

    def _merge(self, partner_ids, dst_partner=None, extra_checks=True):
        """
        Override method to ignore core merge limit
        """
        # super-admin can be used to bypass extra checks
        if self.env.user._is_admin():
            extra_checks = False

        partner_obj = self.env["res.partner"]
        partner_ids = partner_obj.browse(partner_ids).exists()
        if len(partner_ids) < 2:
            return

        merge_limit = self.merge_limit
        if merge_limit and len(partner_ids) > merge_limit:
            raise UserError(
                _(
                    "You cannot merge more than {} contacts together. "
                    "You can re-open the wizard several times if needed.".format(merge_limit),
                )
            )

        # check if the list of partners to merge contains child/parent relation
        child_ids = self.env["res.partner"]
        for partner_id in partner_ids:
            child_ids |= partner_obj.search([("id", "child_of", [partner_id.id])]) - partner_id
        if extra_checks and partner_ids & child_ids:
            raise UserError(
                _(
                    "You cannot merge a contact with one of his parent. "
                    "Only the Administrator can merge contacts with one of his parent.",
                )
            )

        if extra_checks and len(set(partner.email for partner in partner_ids)) > 1:
            raise UserError(
                _(
                    "All contacts must have the same email. "
                    "Only the Administrator can merge contacts with different emails.",
                )
            )

        # remove dst_partner from partners to merge
        if dst_partner and dst_partner in partner_ids:
            src_partners = partner_ids - dst_partner
        else:
            ordered_partners = self._get_ordered_partner(partner_ids.ids)
            dst_partner = ordered_partners[-1]
            src_partners = ordered_partners[:-1]

        _logger.info("dst_partner: %s", dst_partner.id)

        if (
            extra_checks and
            "account.move.line" in self.env and
            self.env["account.move.line"].sudo().search(
                [("partner_id", "in", [partner.id for partner in src_partners])]
            )
        ):
            raise UserError(
                _(
                    "Only the destination contact may be linked to existing Journal Items. Please ask "
                    "the Administrator if you need to merge several contacts linked to existing Journal Items.",
                ),
            )

        # Make the company of all related users consistent with destination partner company
        if dst_partner.company_id:
            partner_ids.mapped("user_ids").sudo().write({
                "company_ids": [(4, dst_partner.company_id.id)],
                "company_id": dst_partner.company_id.id
            })

        # call sub methods to do the merge
        self._update_foreign_keys(src_partners, dst_partner)
        self._update_reference_fields(src_partners, dst_partner)
        self._update_values(src_partners, dst_partner)

        self._log_merge_operation(src_partners, dst_partner)

        # delete source partner, since they are merged
        src_partners.unlink()

    @api.multi
    def _log_merge_operation(self, src_partners, dst_partner):
        """
        Override to save source partners info
        """
        super(BasePartnerMergeAutomaticWizard, self)._log_merge_operation(src_partners, dst_partner)
        for child in src_partners.mapped("child_ids"):
            comment = child.comment
            parent_comment = "Parent ID: {}".format(child.parent_id.id)
            if comment:
                comment += " " + parent_comment
            else:
                comment = parent_comment
            child.comment = comment

    @api.model
    def _update_values(self, src_partners, dst_partner):
        """
        Override to update partner reference of dst_partner with the ones from the src_partners.
        """
        reference_list = [dst_partner.ref]
        for partner in src_partners.filtered(lambda rec: rec.ref):
            reference_list.append(partner.ref)
        if reference_list:
            dst_partner.ref = ";".joint(reference_list)
        super(BasePartnerMergeAutomaticWizard, self)._update_values(src_partners, dst_partner)

    @api.model
    def _generate_query(self, fields, maximum_group=100):
        """
        Override method to prepare a query with new groups
        """
        if "similar_name" not in fields and "without_parent_id" not in fields:
            return super(BasePartnerMergeAutomaticWizard, self)._generate_query(fields, maximum_group=maximum_group)

        group_by_similar_name = "similar_name" in fields
        if group_by_similar_name:
            fields.remove("similar_name")
            if "name" in fields:
                fields.remove("name")

        group_by_without_parent_id = "without_parent_id" in fields
        if group_by_without_parent_id:
            fields.remove("without_parent_id")
            if "parent_id" not in fields:
                fields.append("parent_id")

        # make the list of column to group by in sql query
        sql_fields = []
        for field in fields:
            if field in ["email", "name"]:
                sql_fields.append("lower(%s)" % field)
            elif field in ["vat"]:
                sql_fields.append("replace(%s, ' ', '')" % field)
            else:
                sql_fields.append(field)
        group_fields = ", ".join(sql_fields)

        # where clause : for given group by columns, only keep the 'not null' record
        filters = []
        for field in fields:
            if field in ["email", "name", "vat"]:
                filters.append((field, "IS NOT", "NULL"))
            elif field in ["parent_id"] and group_by_without_parent_id:
                filters.append((field, "IS", "NULL"))
        criteria = " AND ".join("%s %s %s" % (field, operator, value) for field, operator, value in filters)

        # build the query
        text = [
            "SELECT min(id), array_agg(id)",
            "FROM res_partner",
        ]

        if criteria:
            text.append("WHERE %s" % criteria)

        if group_fields:
            text.extend([
                "GROUP BY %s" % group_fields,
            ])

        text.extend([
            "HAVING COUNT(*) >= 2",
            "ORDER BY min(id)",
        ])

        if maximum_group:
            text.append("LIMIT %s" % maximum_group,)

        return " ".join(text)

    @api.multi
    def _action_next_screen(self):
        """
        Override method to call onchange method to recalculate `similarity_threshold` for selected destination partner
        """
        res = super(BasePartnerMergeAutomaticWizard, self)._action_next_screen()
        self._onchange_dst_partner_id()
        return res

    @api.multi
    def _process_query(self, query):
        """
        Override method to call other query process if set similar name option
        """
        self.ensure_one()
        if self.group_by_similar_name:
            self._process_query_by_similar_name(query)
        else:
            super(BasePartnerMergeAutomaticWizard, self)._process_query(query)

    @api.multi
    def _process_query_by_similar_name(self, query):
        """
        Process query with similar name
        """
        model_mapping = self._compute_models()
        # group partner query
        self._cr.execute(query)
        counter = 0
        result = self._cr.fetchall()[0]
        if result:
            min_id = result[0]
            aggr_ids = result[1]
            # To ensure that the used partners are accessible by the user
            partners = self.env["res.partner"].search([("id", "in", aggr_ids)])
            if len(partners) < 2:
                return False
            # exclude partner according to options
            if model_mapping and self._partner_use_in(partners.ids, model_mapping):
                return False

            if fuzz:
                dst_partner = self._get_ordered_partner(aggr_ids)[-1]
                grouped_partners = self._get_grouped_by_same_name_partners(
                    dst_partner,
                    partners,
                    self.similarity_threshold,
                )
                for partner_group in grouped_partners:
                    self.env["base.partner.merge.line"].create({
                        "wizard_id": self.id,
                        "min_id": partner_group.get("dst_partner").id,
                        "aggr_ids": partner_group.get("similar_partners").ids,
                    })
                    counter += 1

        self.write({
            "state": "selection",
            "number_group": counter,
        })

        _logger.info("counter: %s", counter)

    @api.model
    def _get_grouped_by_same_name_partners(self, dst_partner, other_partners, similarity_threshold):
        """
        Return group of partners with the same names
        """
        grouped_partners = unused_partners = self.env["res.partner"]
        result = []
        for partner in other_partners:
            ratio_index = fuzz.ratio(dst_partner.name, partner.name)
            if ratio_index > similarity_threshold:
                grouped_partners |= partner
            else:
                unused_partners |= partner

        if len(grouped_partners) > 1:
            result = [{
                "dst_partner": dst_partner,
                "similar_partners": grouped_partners,
            }]
        if len(unused_partners) > 1:
            dst_partner = self._get_ordered_partner(unused_partners.ids)[-1]
            result += self._get_grouped_by_same_name_partners(dst_partner, unused_partners, similarity_threshold)
        return result
