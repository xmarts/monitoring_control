# -*- coding: utf-8 -*-
import datetime
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, exceptions, _


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    no_validate_sale = fields.Boolean(string='Sin validación de venta', default=False)
    is_carrier = fields.Boolean(string='Es transportista')

    @api.onchange('supplier')
    def onchange_supplier_tr(self):
        if self.supplier == False:
            self.is_carrier = False


class ProductAddition(models.Model):
    _name = "product.addition"
    _inherit = ['mail.thread']

    name = fields.Char(string="Nombre", required=True)
    product_id = fields.Many2one("product.template", string="Producto relacionado", required=True)
    weight = fields.Float(string="Peso", related="product_id.weight", readonly=True)

class ProductAdditionList(models.Model):
    _name = "product.addition.line"

    aditamento_id = fields.Many2one("product.addition", string="Aditamento")
    weight = fields.Float(string="Peso (kg)", related="aditamento_id.weight", readonly=True)
    qty = fields.Float(string="Cantidad")
    total_weight = fields.Float(string="Peso total (kg)", compute="_compute_peso_total")
    picking_id = fields.Many2one("stock.picking")

    @api.one
    def _compute_peso_total(self):
        self.total_weight = self.qty * self.weight
        

class StockPicking(models.Model):
    _inherit = "stock.picking"

    peso_bruto = fields.Float(string="Peso bruto (kg)")
    peso_aditamentos = fields.Float(string="Peso aditamentos (kg)", compute="_compute_peso_aditamentos")
    peso_tara = fields.Float(string="Peso tara (kg)")
    peso_neto = fields.Float(string="Peso neto (kg)", compute="_compute_peso_neto")
    aditamentos_list = fields.One2many("product.addition.line", "picking_id", string="Aditamentos")

    @api.one
    def _compute_peso_aditamentos(self):
        pesot = 0
        for p in self.aditamentos_list:
            pesot = pesot + p.total_weight
        self.peso_aditamentos = pesot

    @api.one
    def _compute_peso_neto(self):
        self.peso_neto = self.peso_bruto - self.peso_aditamentos - self.peso_tara



class TransporterRoutes(models.Model):
    _name = 'sales.route'

    name = fields.Char(string='Nombre de la ruta')
    origin = fields.Char(string='Origen')
    destination = fields.Char(string='Destino')
    time = fields.Float(string='Tiempo aproximado de entrega (Horas).')


# class SaleConfigSettings(models.Model):
#     _inherit = "res.company"

#     user_logistica = fields.Many2one('res.users',string="Usuario validador de logistica")


# class ResConfigSettings(models.TransientModel):
#     _inherit = "res.config.settings"

#     user_logistica = fields.Many2one('res.users', string="Usuario validador de logistica", related='company_id.user_logistica')


class addPermission(models.Model):
    _name = 'res.users'
    _inherit = 'res.users'

    valida_logistica = fields.Boolean(string='Validación logistica de ventas', default=False)


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = 'sale.order'

    #Datos generales en el pedido
    valid_from = fields.Date(string='Vigente desde')
    valid_until = fields.Date(string='Vigente hasta')
    publication_date = fields.Date(string='Fecha de publicación')
    rev_cred_coll = fields.Selection([('pendiente','Pendiente de autorizar'),('aceptado','Aceptado'),('rechazado','Rechazado')],string='Validado por credito y cobranza', default='pendiente')
    rev_logistic = fields.Selection([('pendiente','Pendiente de autorizar'),('aceptado','Aceptado'),('rechazado','Rechazado')],string='Validado por logistica', default='pendiente')
    #Datos en nueva sección
    deadline = fields.Datetime(string='Fecha/Hora de entrega')
    confirmation_number = fields.Char(string='Nº de confirmación')
    observations = fields.Text(string='Observaciones')
    carrier_line = fields.Many2one('res.partner', string='Linea de transportista')
    operator_name = fields.Char(string='Nombre del operador')
    license_number = fields.Char(string='Nº de licencia')
    license_type = fields.Selection([
        ('autom', 'Automovilista'),
        ('chofer', 'Chofer'),
        ('federal', 'Federal')], string='Tipo de licencia')
    route = fields.Many2one('sales.route',string='Ruta')
    clean_unit = fields.Boolean(string='Unidad limpia', default=False)
    no_leaks = fields.Boolean(string='Sin filtraciones de luz o agua', default=False)
    damage_door_floor = fields.Boolean(string='Daños en pisos o puertas', default=False)
    odor_free = fields.Boolean(string='Libre de olores', default=False)
    no_graffiti = fields.Boolean(string='No graffiti', default=False)
    empty_weight = fields.Integer(string='Peso vacio (Kg)')
    loaded_weight = fields.Integer(string='Peso cargado (Kg)')
    transport_observations = fields.Text(string='Observaciones del transporte')
    transport_state = fields.Selection([
        ('accepted','Aceptado'),
        ('rejected','Rechazado'),
        ('in_route','En ruta'),
        ('delivered','Entregado')], string='Estado del transporte')
    request_sent_l = fields.Selection([('si','Si'),('no','No')],string="Solicitud a logistica enviada", readonly=False, default='no')


    @api.onchange('partner_id')
    def onchange_cliente_partner(self):
            if self.partner_id.no_validate_sale == True:
                self.rev_cred_coll = 'aceptado'
                self.rev_logistic = 'aceptado'
                self.request_sent_l = 'si'
            else:
                self.rev_cred_coll = 'pendiente'
                self.rev_logistic = 'pendiente'
                self.request_sent_l = 'no'


    @api.one
    @api.model
    def notificar_logistica(self):
        activity_obj = self.env['mail.activity']
        sale_model = self.env['ir.model'].search([('model','=','sale.order')],limit=1)
        users_l = self.env['res.users'].search([('valida_logistica','=',True)])
        for u in users_l:
            today = datetime.date.today()
            activity_values = {
                'res_id': self.id,
                'res_model_id': sale_model.id,
                'res_model': 'sale.order',
                'date_deadline': today,
                'user_id': u.id,
                'note': 'Validación de la venta '+str(self.name)+' por parte de logistica'
            }
            activity_id = activity_obj.create(activity_values)


    @api.one
    @api.multi
    def write(self, vals):
        cre = vals.get('rev_cred_coll')
        log = vals.get('request_sent_l')
        if cre == 'aceptado':
            if not self.request_sent_l == 'si':
                self.notificar_logistica()
                vals['request_sent_l'] = 'si'
        res = super(SaleOrder, self).write(vals)
        return res


    @api.multi
    def action_confirm(self):
        self.ensure_one()
        res = super(SaleOrder, self).action_confirm()
        if self.partner_id.no_validate_sale == True:
            return res
        else:
            if self.rev_cred_coll == 'pendiente' and self.rev_logistic == 'pendiente':
                raise exceptions.ValidationError('El pedido aun tiene que ser validado por credito y cobranza y logistica')
            if self.rev_cred_coll == 'aceptado' and self.rev_logistic == 'pendiente':
                raise exceptions.ValidationError('El pedido aun tiene que ser validado por logistica')
            if self.rev_cred_coll == 'rechazado' and self.rev_logistic != 'rechazado':
                raise exceptions.ValidationError('El pedido rechazado por credito y cobranza')
            if self.rev_cred_coll != 'rechazado' and self.rev_logistic == 'rechazado':
                raise exceptions.ValidationError('El pedido rechazado por logistica')
            if self.rev_cred_coll == 'rechazado' and self.rev_logistic == 'rechazado':
                raise exceptions.ValidationError('El pedido rechazado por credito y cobranza y logistica')
            if self.rev_cred_coll == 'aceptado' and self.rev_logistic == 'aceptado':
                return res


    @api.multi
    def action_cancel(self):
        self.ensure_one()
        self.rev_cred_coll = False
        self.rev_logistic = False
        res = super(SaleOrder, self).action_cancel()
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    deadline = fields.Datetime(string='Fecha/Hora de entrega', related="order_id.deadline")

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    _name = "purchase.order"

    carrier_payment = fields.Boolean(string="Generar pago a transportista", default=False)
    carrier_payment_type = fields.Selection([('viaje','Por viaje'),('calculado','Calculado')], string="Tipo de pago")
    trip_amount = fields.Monetary(string="Monto por viaje")
    ton_amount = fields.Monetary(string="Precio por tonelada")
    kg_amount = fields.Monetary(string="Precio por Kg", compute="_calcula_kg")

    @api.onchange('carrier_payment')
    def onchange_carrier_payment(self):
        self.carrier_payment_type = ''
        self.trip_amount = 0.0
        self.ton_amount = 0.0
        
    @api.onchange('carrier_payment_type')
    def onchange_carrier_payment_type(self):
        self.trip_amount = 0.0
        self.ton_amount = 0.0

    @api.one
    def _calcula_kg(self):
        self.kg_amount = self.ton_amount / 1000


class MonitoringProducts(models.Model):
    _name = "monitoring.products"

    monitoring_id = fields.Many2one("monitoring.control")
    product_id = fields.Many2one("product.product",string="Producto", readonly=True)
    fecha = fields.Datetime(string="Fecha prevista", readonly=True)
    product_uom = fields.Many2one("product.uom", string="Unidad de medida", readonly=True)
    product_qty = fields.Float(string="Cantidad", readonly=True)
        

class MonitoringMotivos(models.Model):
    _name = "monitoring.motivos"

    name = fields.Char(string="Motivo")
        

class MonitoringControl(models.Model):
    _name="monitoring.control"
    _inherit = ['mail.thread']

    @api.one
    def _document_id(self):
        if self.id < 10:
            self.name = 'DOC0'+str(self.id)
        else:
            self.name = 'DOC'+str(self.id)

    state = fields.Selection([('borrador', 'Borrador'),('aceptado', 'Aceptado'),('rechazado', 'Rechazado')],default='borrador', string="Estado")
    name = fields.Char(string="N° de documento", compute=_document_id)
    tipo_reg = fields.Selection((('entrada','Entrada'),('salida','Salida')),string="Tipo de registro")
    hora_llegada = fields.Datetime(string="Fecha y hora de llegada")
    hora_ingreso = fields.Datetime(string="Fecha y hora de ingreso")
    nombre_chofer = fields.Char(string="Nombre del chofer")
    tipo_trans = fields.Selection((('1ton','1 Tonelada'),('3ton','3 Toneladas'),('5ton','5 Toneladas'),('10ton','10 Toneladas'),('torton','Torton'),('48pi','48 Pies'),('53pi','53 Pies'),('full','Full'),('c20','Contenedor 20'),('c40','Contenedor 40'),('c48','Contenedor 48'),('c53','Contenedor 53')),string="Tipo de transporte")
    placas_tractor = fields.Char(string="Placas del tractor")
    placas_caja = fields.Char(string="Placas de la caja")
    placas_caja_dos = fields.Char(string="Placas de la caja 2")

    #proveedor_linea = fields.Char(string="Proveedor y linea de transporte")

    tipo_licencia = fields.Selection((('autom','Automovilista'),('chofer','Chofer'),('federal','Federal')), string="Tipo de licencia")
    licencia = fields.Char(string="N° de licencia")
    origen = fields.Char(string="Origen")
    destino = fields.Char(string="Destino")
    cedis = fields.Char(string="Cedis")
    purchase_id = fields.Many2one('purchase.order', string="Orden de compra")
    sale_id = fields.Many2one('sale.order', string="Orden de venta")
    provider_id = fields.Many2one('res.partner', string="Proveedor", related="purchase_id.partner_id", readonly=True)
    carrier_id = fields.Many2one('res.partner', string="Transportista")
    purchase_lines = fields.One2many("purchase.order.line", string="Productos", related="purchase_id.order_line")
    sale_lines = fields.One2many("sale.order.line", string="Productos", related="sale_id.order_line")

    motivo_rechazo = fields.Many2one("monitoring.motivos", string="Motivo de rechazo")

    clean_unit = fields.Boolean(string='Unidad limpia', default=False)
    no_leaks = fields.Boolean(string='Sin filtraciones de luz o agua', default=False)
    damage_door_floor = fields.Boolean(string='Daños en pisos o puertas', default=False)
    odor_free = fields.Boolean(string='Libre de olores', default=False)
    no_graffiti = fields.Boolean(string='No graffiti', default=False)
    transport_observations = fields.Text(string='Observaciones del transporte')
    condiciones_trans = fields.Text(string="Condiciones del transporte")


    #Control de calidad
    humidity = fields.Float(string="Humedad %")
    texture = fields.Float(string="Textura %")
    density = fields.Float(string="Densidad")
    brix = fields.Float(string="BRIX")
    temperature = fields.Float(string="Temperatura")
    carbonates = fields.Float(string="Carbonatos")
    a_u = fields.Float(string="A.U.")
    tannins = fields.Float(string="Taninos %")
    rancidity = fields.Float(string="Rancidez")
    agl = fields.Float(string="AGL")
    plague = fields.Float(string="Plaga")


    @api.onchange('purchase_id')
    def onchange_purchase_id(self):
        #Pone en blanco los campos necesarios
        self.carrier_id = ''
        self.nombre_chofer = ''
        self.tipo_licencia = ''
        self.licencia = ''
        self.origen = ''
        self.destino = ''
        self.cedis = ''
        self.clean_unit = False
        self.no_leaks = False
        self.damage_door_floor = False
        self.odor_free = False
        self.no_graffiti = False

    @api.onchange('sale_id')
    def onchange_sale_id(self):
        #Pone en blanco los campos necesarios
        self.carrier_id = ''
        self.nombre_chofer = ''
        self.tipo_licencia = ''
        self.licencia = ''
        self.origen = ''
        self.destino = ''
        self.cedis = ''
        self.clean_unit = False
        self.no_leaks = False
        self.damage_door_floor = False
        self.odor_free = False
        self.no_graffiti = False

        #Carga las lineas del pedido de venta
        if self.sale_id:
            self.carrier_id = self.sale_id.carrier_line
            self.nombre_chofer = self.sale_id.operator_name
            self.tipo_licencia = self.sale_id.license_type
            self.licencia = self.sale_id.license_number
            self.origen = self.sale_id.route.origin
            self.destino = self.sale_id.route.destination
            self.clean_unit = self.sale_id.clean_unit
            self.no_leaks = self.sale_id.no_leaks
            self.damage_door_floor = self.sale_id.damage_door_floor
            self.odor_free = self.sale_id.odor_free
            self.no_graffiti = self.sale_id.no_graffiti

    @api.onchange('tipo_reg')
    def onchange_tipo_reg(self):
        if self.tipo_reg == 'salida':
            self.purchase_id = ''

        if self.tipo_reg == 'entrada':
            self.sale_id = ''

    def action_acept_control(self):
        self.ensure_one()
        if self.state == 'borrador':
            self.state = 'aceptado'

    def action_refuse_control(self):
        self.ensure_one()
        if self.state == 'borrador':
            self.state = 'rechazado'

    def action_draft_control(self):
        self.ensure_one()
        if self.state == 'aceptado' or self.state == 'rechazado':
            self.state = 'borrador'