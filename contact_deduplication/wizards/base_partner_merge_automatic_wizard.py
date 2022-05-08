import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

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
        if self.group_by_no_parent_with_similar_name:
            for partner in self.partner_ids:
                partner.similarity_threshold = fuzz.ratio(self.dst_partner_id.name, partner.name)

    @api.constrains("similarity_threshold", "group_by_no_parent_with_similar_name")
    def _check_graph_model(self):
        """
        Check that `similarity_threshold` has values in the range from 0 to 100
        """
        if (
            self.group_by_no_parent_with_similar_name and
            (self.similarity_threshold < 0 or self.similarity_threshold > 100)
        ):
            raise ValidationError(_("The entered value of \"Similarity Threshold\" must be between 0 and 100."))

    group_by_no_parent_with_same_email = fields.Boolean(
        string="No Parent With Same Email",
        help="Search partners without a parent and with a same email.",
    )
    group_by_no_parent_with_similar_name = fields.Boolean(
        string="No Parent With Similar Name",
        help="Search for partners without a parent and with a similar name.",
    )
    similarity_threshold = fields.Integer(
        string="Similarity Threshold",
        default=50,
        help="Search for partners without a parent and with a similar name "
             "whose similarity threshold is greater than the specified value. "
             "Values must be between 0 and 100",
    )
    save_parent_to_note = fields.Boolean(
        string="Save Parent to Note",
        help="Save to Child Note a Parent ID",
    )

    def _merge(self, partner_ids, dst_partner=None, extra_checks=True):
        """
        Override method to save parent id of contact to note of child contacts
        """
        if self.env.user._is_admin():
            extra_checks = False

        partner_obj = self.env["res.partner"]
        partners = partner_obj.browse(partner_ids).exists()
        if len(partners) < 2:
            return

        if self.save_parent_to_note:
            for child in partners.mapped("child_ids"):
                comment = child.comment
                parent_comment = "Parent ID: {}".format(child.parent_id.id)
                if comment:
                    comment += " " + parent_comment
                else:
                    comment = parent_comment
                child.comment = comment

        super(BasePartnerMergeAutomaticWizard, self)._merge(
            partner_ids,
            dst_partner=dst_partner,
            extra_checks=extra_checks,
        )

    @api.model
    def _generate_query(self, fields, maximum_group=100):
        """
        Override method to prepare a query with new groups
        """
        if "no_parent_with_similar_name" in fields or "no_parent_with_same_email" in fields:
            group_by_no_parent_with_similar_name = False
            if "no_parent_with_similar_name" in fields:
                group_by_no_parent_with_similar_name = True
                fields = ["parent_id"]

            group_by_no_parent_with_same_email = False
            if "no_parent_with_same_email" in fields:
                group_by_no_parent_with_same_email = True
                if "email" not in fields:
                    fields.append("email")
                if "parent_id" not in fields:
                    fields.append("parent_id")

            # make the list of column to group by in sql query
            sql_fields = []
            for field in fields:
                if field in ["email", "name"]:
                    sql_fields.append("lower(%s)" % field)
                elif field in ["vat"]:
                    sql_fields.append("replace(%s, ' ', '')" % field)
                elif field in ["no_parent_with_same_email", "no_parent_with_similar_name"]:
                    # pass the field
                    continue
                else:
                    sql_fields.append(field)
            group_fields = ", ".join(sql_fields)

            # where clause : for given group by columns, only keep the 'not null' record
            filters = []
            for field in fields:
                if field in ["email", "name", "vat"]:
                    filters.append((field, "IS NOT", "NULL"))
                elif field in ["parent_id"] and (group_by_no_parent_with_same_email or group_by_no_parent_with_similar_name):
                    filters.append((field, "IS", "NULL"))
                elif field in ["no_parent_with_same_email", "no_parent_with_similar_name"]:
                    continue
            criteria = " AND ".join("%s %s %s" % (field, operator, value) for field, operator, value in filters)

            # build the query
            text = [
                "SELECT min(id), array_agg(id)",
                "FROM res_partner",
            ]

            if criteria:
                text.append("WHERE %s" % criteria)

            text.extend([
                "GROUP BY %s" % group_fields,
                "HAVING COUNT(*) >= 2",
                "ORDER BY min(id)",
            ])

            if maximum_group:
                text.append("LIMIT %s" % maximum_group,)
            res = " ".join(text)
        else:
            res = super(BasePartnerMergeAutomaticWizard, self)._generate_query(fields, maximum_group=maximum_group)
        return res

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
        Override method to prepare group of partners with similar names
        """
        self.ensure_one()
        if self.group_by_no_parent_with_similar_name:
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
        else:
            super(BasePartnerMergeAutomaticWizard, self)._process_query(query)

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
            print("result", result)
        if len(unused_partners) > 1:
            dst_partner = self._get_ordered_partner(unused_partners.ids)[-1]
            result += self._get_grouped_by_same_name_partners(dst_partner, unused_partners, similarity_threshold)
        return result
