# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, date, time, timedelta
import calendar


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    no_validate_sale = fields.Boolean(string='Sin validación de venta')
    is_carrier = fields.Boolean(string='Es transportista')
    ref_proveedor = fields.Char(string='Referencia proveedor')

    @api.onchange('supplier')
    def onchange_supplier_tr(self):
        if self.supplier == False:
            self.is_carrier = False

class ResUsers(models.Model):
    _inherit = "res.users"
    
    valida_logistica = fields.Boolean(string="Valida Logistica", default=False)

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
    peso_total = fields.Float(string="Peso Total", default=0, compute="_compute_peso_producto_total")

    @api.one
    def _compute_peso_producto_total(self):
        peso = 0
        if self.order_line:
            for p in self.order_line:
                peso = peso + (p.product_id.weight * p.product_uom_qty)
        self.peso_total = peso

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
            today = date.today()
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

    deadline = fields.Datetime(string='Fecha/Hora de entrega', related="order_id.deadline", readonly=True)
    peso_producto = fields.Float(string="Peso", default=0, compute="_compute_peso_producto")

    @api.one
    def _compute_peso_producto(self):
        self.peso_producto = self.product_id.weight * self.product_uom_qty

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"
    _name = "purchase.order.line"
    peso_producto = fields.Float(string="Peso", default=0, compute="_compute_peso_producto")

    @api.one
    def _compute_peso_producto(self):
        self.peso_producto = self.product_id.weight * self.product_qty

class PurchaseProgramedOrder(models.Model):
    _name = "purchase.order.programing"

    def _get_domain(self):
        ids = self.purchase_id.order_line.mapped('product_id').ids
        return [('id', 'in', ids)]

    purchase_id = fields.Many2one("purchase.order")
    product_id = fields.Many2one("product.product", string="Producto", domain=_get_domain)
    product_qty = fields.Float(string="Cantidad a recibir")
    product_uom = fields.Many2one("uom.uom", string="Unidad de medida", related="product_id.uom_id", readonly=True)
    date_planned = fields.Date(string="Fecha planeada")
    state = fields.Selection([('to_program','A programar'),('programed','Programada'),('done','Entregado')], string="Estado", default="to_program")
    monitoring_id = fields.Many2one("monitoring.control")
    
    @api.onchange('purchase_id')
    def _onchange_purchase_id(self):
        if self.purchase_id:
            return {'domain': {
                'product_id': [('id', 'in', self.purchase_id.order_line.mapped('product_id').ids)]}
            }

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    _name = "purchase.order"

    carrier_payment = fields.Boolean(string="Generar pago a transportista", default=False)
    carrier_payment_type = fields.Selection([('viaje','Por viaje'),('calculado','Calculado')], string="Tipo de pago")
    trip_amount = fields.Monetary(string="Monto por viaje")
    ton_amount = fields.Monetary(string="Precio por tonelada")
    kg_amount = fields.Monetary(string="Precio por Kg", compute="_calcula_kg")
    product_programed = fields.One2many("purchase.order.programing", "purchase_id", string="Lista programada")
    peso_total = fields.Float(string="Peso Total", default=0, compute="_compute_peso_producto_total")

    @api.one
    def _compute_peso_producto_total(self):
        peso = 0
        if self.order_line:
            for p in self.order_line:
                peso = peso + (p.product_id.weight * p.product_qty)
        self.peso_total = peso

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
    product_uom = fields.Many2one("uom.uom", string="Unidad de medida", readonly=True)
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

    state = fields.Selection([('ingreso', 'Ingreso'),('aprobado', 'Aprobado'),('salir', 'Por salir'),('egreso', 'Egreso'),('rechazado','Rechazado')],default='ingreso', string="Estado")
    name = fields.Char(string="N° de documento", compute=_document_id)
    tipo_reg = fields.Selection((('entrada','Entrada'),('salida','Salida'),('visitante','Visitante')),string="Tipo de registro", required=True)
    hora_llegada = fields.Datetime(string="Fecha y hora de llegada", default=fields.Datetime.now, required=True)
    hora_ingreso = fields.Datetime(string="Fecha y hora de ingreso", default=fields.Datetime.now, required=True)
    hora_salida = fields.Datetime(string="Fecha y hora de salida", default=fields.Datetime.now)
    nombre_chofer = fields.Char(string="Nombre del chofer")
    tipo_trans = fields.Selection((('1ton','1 Tonelada'),('3ton','3 Toneladas'),('5ton','5 Toneladas'),('10ton','10 Toneladas'),('torton','Torton'),('48pi','48 Pies'),('53pi','53 Pies'),('full','Full'),('c20','Contenedor 20'),('c40','Contenedor 40'),('c48','Contenedor 48'),('c53','Contenedor 53')),string="Tipo de transporte")
    placas_tractor = fields.Char(string="Placas del tractor")
    placas_caja = fields.Char(string="Placas de la caja")
    placas_caja_dos = fields.Char(string="Placas de la caja 2")

    #cambios
    nombre = fields.Char(
        string='Nombre',
    )
    aprobo = fields.Many2one(
         'hr.employee',
         string='Quien Aprobo'
     )
    fecha_aprobacion = fields.Date(
          string='Fecha'
      ) 
    image = fields.Binary(
       
        help="Este campo contiene la imagen utilizada como foto para el empleado, limitada a 1024x1024px.")
    identificacion = fields.Char(
        string='Identificacion',
    )
    num_identificacion = fields.Char(
        string='Numero de Identificacion',
    )
    procedencia = fields.Char(
        string='Procedencia',
    )
    visita =  fields.Many2one(
         'hr.employee',
        string='A quien visita',
    )
    #
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
    sale_lines = fields.One2many("sale.order.line", string="Productos", related="sale_id.order_line", readonly=True)

    motivo_rechazo = fields.Many2one("monitoring.motivos", string="Motivo de rechazo")

    clean_unit = fields.Boolean(string='Unidad limpia', default=False)
    no_leaks = fields.Boolean(string='Sin filtraciones de luz o agua', default=False)
    damage_door_floor = fields.Boolean(string='Daños en pisos o puertas', default=False)
    odor_free = fields.Boolean(string='Libre de olores', default=False)
    no_graffiti = fields.Boolean(string='No graffiti', default=False)
    transport_observations = fields.Text(string='Observaciones del transporte')
    condiciones_trans = fields.Text(string="Condiciones del transporte")
    product_programed = fields.One2many("purchase.order.programing", "monitoring_id", string="Lista programada", delete=False)
    fecha_registro = fields.Date(string="Fecha de creación", default=fields.Date.today())


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

    # @api.model
    # def create(self, values):
    #     res = super(MonitoringControl, self).create(values)
    #     if self.tipo_reg == 'entrada':
    #         for p in self.purchase_id.product_programed:
    #             pop_obj = self.env['purchase.order.programing']
    #             vls = {
    #                 'product_id': p.product_id.id,
    #                 'product_qty': p.product_qty,
    #                 'product_uom': p.product_uom.id,
    #                 'date_planned': p.date_planned,
    #                 'estate': 'received',
    #                 'monitoring_id': res.id,
    #             }
    #             pop_id = pop_obj.create(vls)

    #     return res

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
        related_recordset = self.env["purchase.order.programing"].search([
            ("purchase_id", "=",self.purchase_id.id),
            ("date_planned","=",self.fecha_registro),
            ("state","=","programed")
            ])
        result = []
        for line in related_recordset:
            result.append((0, 0, {'product_id': line.product_id.id,'product_uom': line.product_uom.id,'product_qty': line.product_qty,'date_planned': line.date_planned}))
        self.product_programed = result

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

    def action_salida_control(self):
        self.ensure_one()
        if self.state == 'aprobado':
            self.state = 'salir'

    def action_egreso_control(self):
        self.ensure_one()
        if self.state == 'salir':
            self.state = 'egreso'

    def action_acept_control(self):
        self.ensure_one()
        if self.state == 'ingreso':
            self.state = 'aprobado'

    def action_refuse_control(self):
        self.ensure_one()
        if self.state == 'ingreso':
            self.state = 'rechazado'

    def action_draft_control(self):
        self.ensure_one()
        if self.state == 'aprobado' or self.state == 'salir' or self.state == 'egreso' or self.state == 'rechazado':
            self.state = 'ingreso'

class AddRefProv(models.Model):
    _inherit = 'product.template'

    ref_proveedor = fields.Char(string='Referencia proveedor')
    ref_cliente = fields.Char(string='Referencia cliente')