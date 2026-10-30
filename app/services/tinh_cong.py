"""Tinh cong 1 ngay tu cac phien vao-ra (HAM THUAN, khong doc CSDL) - docs/LOGIC_CHAM_CONG.md muc 6-10, Q21.

Dau vao: gio ca cua ngay (GioCa), cac phien (Phien), cac phep da duyet (PhepNgay), khoang lam viec cua cong nhan va
thoi diem hien tai. Dau ra: TongHopNgay. Moi thoi diem co mui gio; so sanh chinh xac toi giay.
  - Muon: vao phien dau > bat dau + an han -> lam tron LEN (vao - bat dau), tinh tu gio bat dau ca.
  - Ve som: phien cuoi DA DONG va ra < ket thuc -> lam tron LEN (ket thuc - ra). Khong co an han.
  - Phut lam: tong phan giao cua cac phien DA DONG voi gio ca, tru phan giao voi gio nghi, lam tron XUONG.
  - Ra ngoai: khoang trong giua 2 phien lien tiep, trong gio ca, khong tinh gio nghi. Phan nam trong phep
    ra_ngoai_cong_viec khong tinh ra ngoai; phep co tinh_cong thi cong phan do vao phut cong tac.
  - Trang thai ngay (1 ham duy nhat cho bang cong ngay, thang, Excel, API): xem trang_thai_ngay().
"""
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

# phien
TU_DONG, THU_CONG = "tu_dong", "thu_cong"
MO, DONG, THIEU_GIO_RA, HUY = "mo", "dong", "thieu_gio_ra", "huy"

# loai phep (Q21)
VE_SOM, DI_MUON, RA_NGOAI_CONG_VIEC, NGHI_CA_NGAY = "ve_som", "di_muon", "ra_ngoai_cong_viec", "nghi_ca_ngay"
LOAI_PHEP = (VE_SOM, DI_MUON, RA_NGOAI_CONG_VIEC, NGHI_CA_NGAY)

# trang thai ngay (Q10, Q21)
TT_DANG_LAM, TT_THIEU_GIO_RA = "dang_lam", "thieu_gio_ra"
TT_DU_CONG, TT_DI_MUON, TT_VE_SOM, TT_DI_MUON_VE_SOM = "du_cong", "di_muon", "ve_som", "di_muon_ve_som"
TT_DI_MUON_CO_PHEP, TT_VE_SOM_CO_PHEP = "di_muon_co_phep", "ve_som_co_phep"
TT_CHUA_VAO, TT_VANG, TT_NGHI_TUAN, TT_CHUA_DEN = "chua_vao", "vang", "nghi_tuan", "chua_den"
TT_NGOAI_THOI_GIAN, TT_NGHI_PHEP = "ngoai_thoi_gian_lam_viec", "nghi_phep"
CO_CONG = frozenset({TT_DU_CONG, TT_DI_MUON, TT_VE_SOM, TT_DI_MUON_VE_SOM, TT_DI_MUON_CO_PHEP, TT_VE_SOM_CO_PHEP})
TEN_TRANG_THAI = {
    TT_DANG_LAM: "Đang làm", TT_THIEU_GIO_RA: "Thiếu giờ ra", TT_DU_CONG: "Đủ công", TT_DI_MUON: "Đi muộn",
    TT_VE_SOM: "Về sớm", TT_DI_MUON_VE_SOM: "Đi muộn, về sớm", TT_DI_MUON_CO_PHEP: "Đi muộn có phép",
    TT_VE_SOM_CO_PHEP: "Về sớm có phép", TT_CHUA_VAO: "Chưa vào", TT_VANG: "Vắng", TT_NGHI_TUAN: "Nghỉ tuần",
    TT_CHUA_DEN: "Chưa đến", TT_NGOAI_THOI_GIAN: "Ngoài thời gian làm việc", TT_NGHI_PHEP: "Nghỉ phép",
}
THU = {"thu_hai": 0, "thu_ba": 1, "thu_tu": 2, "thu_nam": 3, "thu_sau": 4, "thu_bay": 5, "chu_nhat": 6}


def phut_xuong(td: timedelta) -> int:
    """So phut, lam tron XUONG, khong am."""
    return max(0, int(td.total_seconds() // 60))


def phut_len(td: timedelta) -> int:
    """So phut, lam tron LEN (5 phut 1 giay -> 6), khong am. Tinh bang micro giay de khong sai so so thuc."""
    us = td // timedelta(microseconds=1)
    return max(0, -(-us // 60_000_000))


@dataclass(frozen=True)
class GioCa:
    """Gio ca cua 1 ngay cu the (thoi diem co mui gio)."""
    bat_dau: datetime
    ket_thuc: datetime
    nghi_tu: datetime
    nghi_den: datetime
    an_han: int = 5      # phut
    vao_som: int = 60    # phut

    @property
    def mo_cua_vao(self) -> datetime:
        return self.bat_dau - timedelta(minutes=self.vao_som)

    @property
    def phut_chuan(self) -> int:
        """So phut lam chuan cua ca = gio ca - phan nghi nam trong ca."""
        return phut_xuong(self.ket_thuc - self.bat_dau - _do_dai(_giao([(self.bat_dau, self.ket_thuc)],
                                                                       [(self.nghi_tu, self.nghi_den)])))


@dataclass(frozen=True)
class Phien:
    vao: datetime
    ra: datetime | None = None
    trang_thai: str = DONG
    nguon_vao: str = TU_DONG
    nguon_ra: str | None = None


@dataclass(frozen=True)
class PhepNgay:
    """Phep da duyet cua ngay dang tinh. tu / den: thoi diem (theo loai: ve_som dung tu, di_muon dung den)."""
    loai: str
    tu: datetime | None = None
    den: datetime | None = None
    tinh_cong: bool = False


@dataclass
class TongHopNgay:
    check_in: datetime | None = None
    check_out: datetime | None = None
    late_minutes: int = 0
    early_leave_minutes: int = 0
    worked_minutes: int = 0
    so_lan_ra_ngoai: int = 0
    phut_ra_ngoai: int = 0
    phut_cong_tac: int = 0
    cong_quy_doi: float = 0.0
    trang_thai_ngay: str = TT_CHUA_VAO
    ngay_cong: int = 0
    co_sua_tay: bool = False
    co_ra_ngoai: bool = False
    lam_ngay_nghi: bool = False
    thieu_gio_ra: bool = False
    muon_co_phep: bool = False   # di muon nhung co phep (vao <= gio du kien + dung sai)
    som_co_phep: bool = False    # ve som nhung co phep (ra >= gio duoc ve - dung sai)
    can_giai_trinh: bool = False  # muon / ve som KHONG phep vuot nguong, chua "xac nhan khong phep"
    phien: list = field(default_factory=list)  # cac phien da tinh (khong tinh phien huy), theo gio vao


# --- khoang thoi gian ---
def _giao(a: list[tuple], b: list[tuple]) -> list[tuple]:
    """Giao cua 2 danh sach khoang [tu, den)."""
    out = []
    for a1, a2 in a:
        for b1, b2 in b:
            lo, hi = max(a1, b1), min(a2, b2)
            if lo < hi:
                out.append((lo, hi))
    return out


def _tru(a: list[tuple], b: list[tuple]) -> list[tuple]:
    """Cac khoang trong a, bo di moi phan nam trong b."""
    for b1, b2 in b:
        nxt = []
        for a1, a2 in a:
            if b2 <= a1 or a2 <= b1:
                nxt.append((a1, a2))
                continue
            if a1 < b1:
                nxt.append((a1, b1))
            if b2 < a2:
                nxt.append((b2, a2))
        a = nxt
    return a


def _do_dai(ds: list[tuple]) -> timedelta:
    return sum((b - a for a, b in ds), timedelta(0))


def thoi_gian_lam(tu: datetime, den: datetime, ca: GioCa) -> timedelta:
    """Phan cua [tu, den] nam trong gio ca va ngoai gio nghi."""
    return _do_dai(_tru(_giao([(tu, den)], [(ca.bat_dau, ca.ket_thuc)]), [(ca.nghi_tu, ca.nghi_den)]))


# --- tong hop 1 ngay ---
def tong_hop(ngay: date, ca: GioCa, phien: list[Phien], phep: list[PhepNgay] = (), *, now: datetime,
             ngay_vao_lam: date | None = None, ngay_nghi_viec: date | None = None, nghi_tuan=frozenset({6}),
             dung_sai_phut: int = 15, nguong_phut: int = 15, da_xac_nhan_khong_phep: bool = False) -> TongHopNgay:
    """Tinh cong 1 ngay. phien: moi phien cua ngay (ke ca phien huy, de biet co sua tay). nghi_tuan: cac thu trong tuan
    (0 = thu Hai ... 6 = Chu nhat) la ngay nghi hang tuan."""
    r = TongHopNgay()
    r.co_sua_tay = any(p.nguon_vao == THU_CONG or p.nguon_ra == THU_CONG or p.trang_thai == HUY for p in phien)
    ps = sorted((p for p in phien if p.trang_thai != HUY), key=lambda p: p.vao)
    r.phien = ps
    dung_sai = timedelta(minutes=dung_sai_phut)
    if ps:
        first, last = ps[0], ps[-1]
        r.check_in = first.vao
        r.check_out = last.ra if last.trang_thai == DONG else None
        if first.vao > ca.bat_dau + timedelta(minutes=ca.an_han):
            r.late_minutes = phut_len(first.vao - ca.bat_dau)
        if r.check_out is not None and r.check_out < ca.ket_thuc:
            r.early_leave_minutes = phut_len(ca.ket_thuc - r.check_out)
        r.worked_minutes = phut_xuong(sum((thoi_gian_lam(p.vao, p.ra, ca) for p in ps if p.trang_thai == DONG and p.ra),
                                          timedelta(0)))
        # ra ngoai / cong tac: khoang trong giua 2 phien lien tiep (phien truoc phai co gio ra)
        cong_tac = [(p.tu, p.den) for p in phep if p.loai == RA_NGOAI_CONG_VIEC and p.tinh_cong and p.tu and p.den]
        co_phep = [(p.tu, p.den) for p in phep if p.loai == RA_NGOAI_CONG_VIEC and p.tu and p.den]
        ra_ngoai, phut_ct = timedelta(0), timedelta(0)
        for a, b in zip(ps, ps[1:]):
            if a.ra is None or b.vao <= a.ra:
                continue
            trong_ca = _tru(_giao([(a.ra, b.vao)], [(ca.bat_dau, ca.ket_thuc)]), [(ca.nghi_tu, ca.nghi_den)])
            phut_ct += _do_dai(_giao(trong_ca, cong_tac))
            con_lai = _do_dai(_tru(trong_ca, co_phep))
            if con_lai > timedelta(0):
                ra_ngoai += con_lai
                r.so_lan_ra_ngoai += 1
        r.phut_ra_ngoai, r.phut_cong_tac = phut_xuong(ra_ngoai), phut_xuong(phut_ct)
        r.co_ra_ngoai = r.phut_ra_ngoai > 0
        # phep di muon / ve som (dung sai: vao toi da den + dung sai; ra som nhat tu - dung sai)
        r.muon_co_phep = r.late_minutes > 0 and any(
            p.loai == DI_MUON and p.den and r.check_in <= p.den + dung_sai for p in phep)
        r.som_co_phep = r.early_leave_minutes > 0 and any(
            p.loai == VE_SOM and p.tu and r.check_out >= p.tu - dung_sai for p in phep)
        r.thieu_gio_ra = any(p.trang_thai == THIEU_GIO_RA for p in ps)
        r.lam_ngay_nghi = ngay.weekday() in nghi_tuan
    if ca.phut_chuan > 0:
        r.cong_quy_doi = round((r.worked_minutes + r.phut_cong_tac) / ca.phut_chuan, 2)
    r.trang_thai_ngay = trang_thai_ngay(ngay, r, phep, now=now, ca=ca, ngay_vao_lam=ngay_vao_lam,
                                        ngay_nghi_viec=ngay_nghi_viec, nghi_tuan=nghi_tuan)
    r.ngay_cong = 1 if r.trang_thai_ngay in CO_CONG else 0
    # can giai trinh: muon / ve som KHONG phep qua nguong. Ve som chi xet khi ca cua ngay do da ket thuc (truoc do co
    # the chi la ra an trua / ra ngoai roi vao lai).
    muon = r.late_minutes > nguong_phut and not r.muon_co_phep
    som = r.early_leave_minutes > nguong_phut and not r.som_co_phep and now >= ca.ket_thuc
    r.can_giai_trinh = bool(ps) and (muon or som) and not da_xac_nhan_khong_phep \
        and r.trang_thai_ngay not in (TT_DANG_LAM, TT_THIEU_GIO_RA)
    return r


def trang_thai_ngay(ngay: date, r: TongHopNgay, phep: list[PhepNgay], *, now: datetime, ca: GioCa,
                    ngay_vao_lam: date | None, ngay_nghi_viec: date | None, nghi_tuan) -> str:
    """Trang thai chinh cua 1 ngay (Q10, Q21). Ngay co phien: dang_lam > thieu_gio_ra > muon/ve som/du cong.
    Ngay khong co phien: ngoai thoi gian lam viec > nghi tuan > nghi phep > chua den > chua vao (hom nay) > vang."""
    if r.phien:
        if any(p.trang_thai == MO for p in r.phien):
            return TT_DANG_LAM
        if r.thieu_gio_ra:
            return TT_THIEU_GIO_RA
        muon = r.late_minutes > 0 and not r.muon_co_phep
        som = r.early_leave_minutes > 0 and not r.som_co_phep
        if muon and som:
            return TT_DI_MUON_VE_SOM
        if muon:
            return TT_DI_MUON
        if som:
            return TT_VE_SOM
        if r.muon_co_phep:
            return TT_DI_MUON_CO_PHEP
        if r.som_co_phep:
            return TT_VE_SOM_CO_PHEP
        return TT_DU_CONG
    if (ngay_vao_lam and ngay < ngay_vao_lam) or (ngay_nghi_viec and ngay > ngay_nghi_viec):
        return TT_NGOAI_THOI_GIAN
    if ngay.weekday() in nghi_tuan:
        return TT_NGHI_TUAN
    if any(p.loai == NGHI_CA_NGAY for p in phep):
        return TT_NGHI_PHEP
    hom_nay = now.astimezone(ca.bat_dau.tzinfo).date()
    if ngay > hom_nay:
        return TT_CHUA_DEN
    if ngay == hom_nay:
        return TT_CHUA_VAO
    return TT_VANG


def nghi_tuan_tu_cau_hinh(att_cfg: dict) -> frozenset:
    """attendance.ngay_nghi_tuan (vd [chu_nhat]) -> {6}."""
    names = att_cfg.get("ngay_nghi_tuan") or []
    unknown = [n for n in names if n not in THU]
    if unknown:
        raise ValueError(f"attendance.ngay_nghi_tuan co gia tri khong hop le: {unknown} (dung {', '.join(THU)})")
    return frozenset(THU[n] for n in names)
