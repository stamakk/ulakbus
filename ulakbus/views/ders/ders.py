# -*-  coding: utf-8 -*-
"""
"""

# Copyright (C) 2015 ZetaOps Inc.
#
# This file is licensed under the GNU General Public License v3
# (GPLv3).  See LICENSE.txt for details.

from pyoko import ListNode
from zengine import forms
from zengine.forms import fields
from zengine.views.crud import CrudView, form_modifier
from ulakbus.models.ogrenci import Program, Okutman, DegerlendirmeNot, Ders, Sube, Sinav, OgrenciDersi, Donem
from ulakbus.models.ogrenci import DegerlendirmeNot, Ogrenci, OgrenciProgram
from pyoko.exceptions import ObjectDoesNotExist
from collections import OrderedDict


def prepare_choices_for_model(model, **kwargs):
    return [(m.key, m.__unicode__()) for m in model.objects.filter(**kwargs)]


def okutman_choices():
    return [{'name': name, 'value': value} for value, name in prepare_choices_for_model(Okutman)]


class ProgramBilgisiForm(forms.JsonForm):
    class Meta:
        include = ['program']

    sec = fields.Button("Seç", cmd="program_sec")


class DersBilgileriForm(forms.JsonForm):
    class Meta:
        include = ['ad', 'kod', 'tanim', 'aciklama', 'onkosul', 'uygulama_saati', 'teori_saati',
                   'ects_kredisi',
                   'yerel_kredisi', 'zorunlu', 'ders_dili', 'ders_turu', 'ders_amaci',
                   'ogrenme_ciktilari',
                   'ders_icerigi', 'ders_kategorisi', 'ders_kaynaklari', 'ders_mufredati',
                   'verilis_bicimi', 'donem',
                   'ders_koordinatoru']

    kaydet = fields.Button("Kaydet", cmd="kaydet", flow="end")
    kaydet_yeni_kayit = fields.Button("Kaydet/Yeni Kayıt Ekle", cmd="kaydet", flow="start")


class DersEkle(CrudView):
    class Meta:
        model = "Ders"

    def program_sec(self):
        self.set_form_data_to_object()
        self.current.task_data['program_id'] = self.object.program.key

    def kaydet(self):
        self.set_form_data_to_object()
        self.object.program = Program.objects.get(self.current.task_data['program_id'])
        self.save_object()
        # self.current.task_data['next'] = self.current.input['next']

    def ders_bilgileri(self):
        self.form_out(DersBilgileriForm(self.object, current=self.current))

    def program_bilgisi(self):
        self.form_out(ProgramBilgisiForm(self.object, current=self.current))


class SecimForm(forms.JsonForm):
    sec = fields.Button("Sec", cmd="ders_sec")


class ProgramForm(forms.JsonForm):
    sec = fields.Button("Sec", cmd="ders_sec")


class SubelendirmeForm(forms.JsonForm):
    kaydet_ders = fields.Button("Kaydet ve Ders Seçim Ekranına Dön", cmd="subelendirme_kaydet",
                                flow="ders_okutman_formu")
    program_sec = fields.Button("Kaydet ve Program Seçim Ekranına Dön", cmd="subelendirme_kaydet",
                                flow="program_sec")
    bilgi_ver = fields.Button("Tamamla ve Hocaları Bilgilendir", cmd="subelendirme_kaydet",
                              flow="bilgi_ver")

    class Subeler(ListNode):
        ad = fields.String('Sube Adi')
        kontenjan = fields.Integer('Sube Kontenjani')
        dis_kontenjan = fields.Integer('Sube Dis Kontenjani')
        okutman = fields.String('Okutman', choices=okutman_choices)


class NotGirisForm(forms.JsonForm):
    class Ogrenciler(ListNode):
        ogrenci_no = fields.String('No')
        ad_soyad = fields.String('Ad Soyad')
        degerlendirme = fields.Integer('Not')
        aciklama = fields.String('Aciklama')
        key = fields.String('KKKKey', hidden=True)


class DersSubelendirme(CrudView):
    class Meta:
        model = "Sube"

    def program_sec(self):
        _form = ProgramForm(current=self.current)
        choices = prepare_choices_for_model(Program)
        _form.program = fields.Integer(choices=choices)
        self.form_out(_form)

    def ders_sec(self):
        self.set_client_cmd('form')
        self.output['objects'] = [['Dersler'], ]

        if 'program' in self.current.input['form']:
            self.current.task_data['program'] = self.current.input['form']['program']

        p = Program.objects.get(key=self.current.task_data['program'])
        dersler = Ders.objects.filter(program=p)
        # dersler = Ders.objects.filter()
        for d in dersler:
            ders = "{} - {} ({} ECTS)".format(d.kod, d.ad, d.ects_kredisi)
            subeler = Sube.objects.filter(ders=d)
            sube = []
            for s in subeler:
                sube.append(
                        {
                            "sube_ad": s.ad,
                            "okutman_ad": s.okutman.ad,
                            "okutman_soyad": s.okutman.soyad,
                            "okutman_unvan": s.okutman.unvan,
                            "kontenjan": s.kontenjan,
                        }
                )

            ders_subeleri = ["{okutman_unvan} {okutman_ad}"
                             "{okutman_soyad}, Sube:{sube_ad} Kontenjan{kontenjan} \n".format(**sb)
                             for sb in sube]

            item = {
                "fields": ["{} \n {}".format(ders, ders_subeleri), ],
                "actions": [
                    {'name': 'Subelendir', 'cmd': 'ders_okutman_formu', 'show_as': 'button',
                     'object_key': 'sube'},
                ],
                "key": d.key
            }
            self.output['objects'].append(item)

    def ders_okutman_formu(self):
        # subelendirme icin secilen dersi getir
        ders = Ders.objects.get(key=self.current.input['sube'])
        # sonraki adimlar icin task data icine koy
        self.current.task_data['ders_key'] = ders.key

        # formu olusturmaya basla
        subelendirme_form = SubelendirmeForm(current=self.current,
                                             title='%s / %s dersi icin subelendirme' % (
                                                 ders.donem, ders))
        # formun sube listesini olustur
        subeler = Sube.objects.filter(ders=ders)
        for sube in subeler:
            subelendirme_form.Subeler(ad=sube.ad, kontenjan=sube.kontenjan,
                                      dis_kontenjan=sube.dis_kontenjan,
                                      okutman=sube.okutman.key)

        self.form_out(subelendirme_form)

    def subelendirme_kaydet(self):
        sb = self.input['form']['Subeler']
        ders = self.current.task_data['ders_key']
        mevcut_subeler = Sube.objects.filter(ders_id=ders)
        for s in sb:
            okutman = s['okutman']
            sube, is_new = Sube.objects.get_or_create(okutman_id=okutman, ders_id=ders)
            # mevcut_subelerden cikar
            mevcut_subeler = list(set(mevcut_subeler) - {sube})
            sube.kontenjan = s['kontenjan']
            sube.dis_kontenjan = s['dis_kontenjan']
            sube.ad = s['ad']
            sube.save()
        # mevcut subelerde kalanlari sil
        for s in mevcut_subeler:
            s.delete()

    def bilgi_ver(self):
        sbs = Sube.objects.filter(ders_id=self.current.task_data['ders_key'])
        okutmanlar = [s.okutman.__unicode__() for s in sbs]

        self.current.output['msgbox'] = {
            'type': 'info', "title": 'Mesaj Iletildi',
            "msg": 'Şubelendirme Bilgileri şu hocalara iletildi: %s' % ", ".join(okutmanlar)}


class NotGirisi(CrudView):
    class Meta:
        model = "DegerlendirmeNot"

    def ders_secim(self):
        _form = forms.JsonForm(current=self.current, title="Ders Seçim Formu")
        user = self.current.user
        subeler = Sube.objects.filter(okutman_id=self.get_okutman_key)
        _form.sube = fields.Integer("Sube Seçiniz",
                                    choices=prepare_choices_for_model(Sube, okutman_id=self.get_okutman_key))
        _form.sec = fields.Button("Seç", cmd="Ders Şubesi Seçin")
        self.form_out(_form)

    def sinav_sec(self):
        _form = forms.JsonForm(current=self.current, title="Sınav Seçim Formu")

        try:
            sube_key = self.current.input['form']['sube']
        except:
            sube_key = self.current.task_data["sube"]

        _form.sinav = fields.Integer("Sınav Seçiniz", choices=prepare_choices_for_model(Sinav, sube_id=sube_key))
        self.current.task_data["sube"] = sube_key
        _form.sec = fields.Button("Seç", cmd="Sınav Seçin")
        self.form_out(_form)

    def sinav_kontrol(self):
        sinav_key = self.current.input['form']['sinav']
        self.current.task_data['sinav_key'] = sinav_key
        sinav = Sinav.objects.get(sinav_key)
        self.current.task_data['sinav_degerlendirme'] = sinav.degerlendirme

    def not_girisi(self):
        _form = NotGirisForm(current=self.current, title="Not Giriş Formu")
        sinav_key = self.current.task_data['sinav_key']
        sube_key = self.current.task_data["sube"]
        sinav = Sinav.objects.get(sinav_key)

        try:
            ogrenciler = self.current.task_data["notlar"]
            for ogr in ogrenciler:
                _form.Ogrenciler(ad_soyad='%s' % (ogr['ad_soyad']),
                                 ogrenci_no=ogr['ogrenci_no'], degerlendirme=ogr['degerlendirme'],
                                 aciklama=ogr['aciklama'],
                                 key=ogr['key'])
        except:
            ogrenciler = OgrenciDersi.objects.filter(ders_id=sube_key)

            for ogr in ogrenciler:
                try:
                    degerlendirme = DegerlendirmeNot.objects.get(sinav=sinav, ogrenci=ogr.ogrenci_program.ogrenci)
                    puan = degerlendirme.puan
                    aciklama = degerlendirme.aciklama
                    degerlendirme_key = degerlendirme.key
                except:
                    puan = 0
                    aciklama = ""
                    degerlendirme_key = ""

                _form.Ogrenciler(ad_soyad='%s %s' % (ogr.ogrenci_program.ogrenci.ad, ogr.ogrenci_program.ogrenci.soyad),
                                 ogrenci_no=ogr.ogrenci_program.ogrenci_no, degerlendirme=puan, aciklama=aciklama,
                                 key=degerlendirme_key)

        _form.kaydet = fields.Button("Önizleme", cmd="not_kontrol")
        self.form_out(_form)
        self.current.output["meta"]["allow_actions"] = False

    def not_kontrol(self):
        _form = forms.JsonForm(current=self.current, title="Not Önizleme Ekranı")

        try:  # Eğer not_kontrol aşamasından geri dönülmemişse öğrenci notlarını için formdan gelen veriyi kullan
            ogrenci_notlar = self.current.input['form']['Ogrenciler']
            self.current.task_data["notlar"] = ogrenci_notlar

            notlar = []
            for ogr in ogrenci_notlar:
                ogrnot = OrderedDict({})
                ogrnot['Öğrenci No'] = ogr['ogrenci_no']
                ogrnot['Adı Soyadı'] = ogr['ad_soyad']
                ogrnot['Değerlendirme'] = ogr['degerlendirme']
                ogrnot['Açıklama'] = ogr['aciklama']
                notlar.append(ogrnot)

        except:  # Eğer not_kontrol aşamasından geri dönülmüşse task_data'dan gelen not verilerini kullan
            sinav_key = self.current.task_data['sinav_key']
            sube_key = self.current.task_data["sube"]
            sinav = Sinav.objects.get(sinav_key)
            ogrenciler = OgrenciDersi.objects.filter(ders_id=sube_key)
            notlar = []

            for ogr in ogrenciler:
                try:  # Öğrenciye ait notlar daha önceden girilmiş mi?
                    degerlendirme = DegerlendirmeNot.objects.get(sinav=sinav, ogrenci=ogr.ogrenci_program.ogrenci)
                    puan = degerlendirme.puan
                    aciklama = degerlendirme.aciklama
                except:
                    puan = 0
                    aciklama = ""

                ogrnot = OrderedDict({})
                ogrnot['Öğrenci No'] = ogr.ogrenci_program.ogrenci_no
                ogrnot['Adı Soyadı'] = '%s %s' % (ogr.ogrenci_program.ogrenci.ad, ogr.ogrenci_program.ogrenci.soyad)
                ogrnot['Değerlendirme'] = puan
                ogrnot['Açıklama'] = aciklama
                notlar.append(ogrnot)

        # Eğer notlar okutman tarından onaylanmışsa (teslim edilmişse) uyarı göster

        if self.current.task_data['sinav_degerlendirme']:
            self.current.output['msgbox'] = {

                'type': 'info', "title": 'Notlar Onaylandı',
                "msg": 'Bu derse ait notlar onaylanmış olduğu için içeriği değiştirilemez.'

            }

        else:  # Eğer notlar hala onaylanmamışsa (teslim edilmemişse) form düğmelerini göster

            _form.not_onay = fields.Boolean("Sınav Notlarını Onaylıyorum (Bu işlem geri alınmaz!)")
            _form.not_duzenle = fields.Button("Notları Düzenle", cmd="not_girisi", flow="not_giris_formuna_don")
            _form.kaydet = fields.Button("Kaydet", cmd="not_kaydet", flow="end")
            _form.kaydet_ve_ders_sec = fields.Button("Kaydet ve Ders Seçim Ekranına Dön", cmd="ders_sec",
                                                     flow="ders_adimina_don")
            _form.kaydet_ve_sinav_sec = fields.Button("Kaydet ve Sınav Seçim Ekranına Dön", cmd="sinav_sec",
                                                      flow="sinav_adimina_don")

        self.current.output['object'] = {
            "type": "table-multiRow",
            "fields": notlar,
            "actions": False
        }
        self.form_out(_form)

    def not_kaydet(self):
        term = Donem.objects.filter(guncel=True)[0]
        sinav_key = self.current.task_data["sinav_key"]
        sube_key = self.current.task_data["sube"]

        sinav = Sinav.objects.get(sinav_key)
        ders = sinav.ders

        for ogrenci_not in self.current.task_data["notlar"]:

            try:
                ogr_data = OgrenciProgram.objects.get(ogrenci_no=ogrenci_not['ogrenci_no'])

                if ogrenci_not['key']:
                    ogr_not = DegerlendirmeNot.objects.get(ogrenci_not['key'])
                else:
                    ogr_not = DegerlendirmeNot()

                ogr_not.puan = ogrenci_not['degerlendirme']
                ogr_not.aciklama = ogrenci_not['aciklama']
                ogr_not.ogrenci_no = ogrenci_not['ogrenci_no']
                ogr_not.donem = '%s' % term.ad
                ogr_not.yil = term.baslangic_tarihi.year
                ogr_not.ogretim_elemani = self.get_okutman_name_surname
                ogr_not.ders = ders
                ogr_not.sinav = sinav
                ogr_not.ogrenci = ogr_data.ogrenci
                ogr_not.save()

            except ObjectDoesNotExist:
                raise ObjectDoesNotExistError("Ogrenci Bulunamadı %s" % ogrenci_not['ogrenci_no'])

        # Okutman notları onayladığını (teslim ettiğini) bildirmişse

        if self.current.input['form']['not_onay']:
            sinav.degerlendirme = True
            sinav.save()

    def kayit_bilgisi_ver(self):
        import datetime
        sinav_key = self.current.task_data["sinav_key"]
        sinav = Sinav.objects.get(sinav_key)
        sinav_tarihi = sinav.tarih.strftime("%d/%m/%Y")

        self.current.output['msgbox'] = {
            'type': 'info', "title": 'Notlar Kaydedildi',
            "msg": '%s dersine ait %s tarihli sınav notları kaydedildi' % (sinav.ders.ad, sinav_tarihi)}

    @property
    def get_okutman_key(self):

        '''
        Harici okutman ve okutman kayıt key'lerinin ayrımı için
        '''
        return self.current.user.personel.okutman.key if self.current.user.personel.key else self.current.user.harici_okutman.okutman.key

    @property
    def get_okutman_name_surname(self):
        '''
        Harici okutman ve okutman ad,soyad ayrımı için
        '''
        return "%s %s" % (self.current.user.personel.okutman.ad,
                          self.current.user.personel.okutman.soyad) if self.current.user.personel.key else "%s %s" % (
            self.current.user.harici_okutman.ad, self.current.user.harici_okutman.soyad)

    @form_modifier
    def not_form_inline_edit(self, serialized_form):
        '''
        NotGirisForm'da inline edit elde etmek için
        '''
        if 'Ogrenciler' in serialized_form['schema']['properties']:
            serialized_form['inline_edit'] = ['degerlendirme', 'aciklama']