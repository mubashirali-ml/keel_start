"""The 50 US states plus DC with their official filing-office and name-search pages (ADR-0008).

Curated by T-001. ``filing_office_url`` is the Secretary of State (or equivalent) business
division home page; ``name_search_url`` is the official business entity / name search page.
State business-name availability can't be checked through a free API, so the Name Agent
links founders to these pages (ADR-0011).
"""

from __future__ import annotations

from pydantic import BaseModel

from .errors import InvalidStateError

__all__ = ["US_STATES", "StateInfo", "state_info"]


class StateInfo(BaseModel):
    code: str
    name: str
    filing_office_url: str  # Secretary of State business division home page
    name_search_url: str  # official business entity / name search page


_DATA: tuple[tuple[str, str, str, str], ...] = (
    ("AL", "Alabama", "https://www.sos.alabama.gov/business-entities", "https://arc-sos.state.al.us/CGI/CORPNAME.MBR/INPUT"),
    ("AK", "Alaska", "https://www.commerce.alaska.gov/web/cbpl/Corporations.aspx", "https://www.commerce.alaska.gov/cbp/main/search/entities"),
    ("AZ", "Arizona", "https://azcc.gov/divisions/corporations", "https://ecorp.azcc.gov/EntitySearch/Index"),
    ("AR", "Arkansas", "https://www.sos.arkansas.gov/business-commercial-services-bcs", "https://www.ark.org/corp-search/"),
    ("CA", "California", "https://www.sos.ca.gov/business-programs", "https://bizfileonline.sos.ca.gov/search/business"),
    ("CO", "Colorado", "https://www.sos.state.co.us/pubs/business/main.html", "https://www.sos.state.co.us/biz/BusinessEntityCriteriaExt.do"),
    ("CT", "Connecticut", "https://portal.ct.gov/sots/business-services", "https://service.ct.gov/business/s/onlinebusinesssearch"),
    ("DE", "Delaware", "https://corp.delaware.gov/", "https://icis.corp.delaware.gov/ecorp/entitysearch/namesearch.aspx"),
    ("DC", "District of Columbia", "https://dlcp.dc.gov/service/corporate-registration", "https://corponline.dlcp.dc.gov/"),
    ("FL", "Florida", "https://dos.fl.gov/sunbiz/", "https://search.sunbiz.org/Inquiry/CorporationSearch/ByName"),
    ("GA", "Georgia", "https://sos.ga.gov/corporations-division", "https://ecorp.sos.ga.gov/BusinessSearch"),
    ("HI", "Hawaii", "https://cca.hawaii.gov/breg/", "https://hbe.ehawaii.gov/documents/search.html"),
    ("ID", "Idaho", "https://sos.idaho.gov/business-services/", "https://sosbiz.idaho.gov/search/business"),
    ("IL", "Illinois", "https://www.ilsos.gov/departments/business_services/home.html", "https://apps.ilsos.gov/businessentitysearch/"),
    ("IN", "Indiana", "https://www.in.gov/sos/business/", "https://bsd.sos.in.gov/publicbusinesssearch"),
    ("IA", "Iowa", "https://sos.iowa.gov/business/", "https://sos.iowa.gov/search/business/search.aspx"),
    ("KS", "Kansas", "https://sos.ks.gov/businesses/businesses.html", "https://www.sos.ks.gov/eforms/BusinessEntity/Search.aspx"),
    ("KY", "Kentucky", "https://www.sos.ky.gov/bus/business-filings/Pages/default.aspx", "https://web.sos.ky.gov/bussearchnprofile/search.aspx"),
    ("LA", "Louisiana", "https://www.sos.la.gov/BusinessServices/Pages/default.aspx", "https://coraweb.sos.la.gov/commercialsearch/commercialsearch.aspx"),
    ("ME", "Maine", "https://www.maine.gov/sos/cec/corp/", "https://apps3.web.maine.gov/nei-sos-icrs/ICRS?MainPage=x"),
    ("MD", "Maryland", "https://dat.maryland.gov/businesses/Pages/default.aspx", "https://egov.maryland.gov/BusinessExpress/EntitySearch"),
    ("MA", "Massachusetts", "https://www.sec.state.ma.us/divisions/corporations/corporations.htm", "https://corp.sec.state.ma.us/corpweb/CorpSearch/CorpSearch.aspx"),
    ("MI", "Michigan", "https://www.michigan.gov/lara/bureau-list/cscl/corps", "https://cofs.lara.state.mi.us/SearchApi/Search/Search"),
    ("MN", "Minnesota", "https://www.sos.state.mn.us/business-liens/", "https://mblsportal.sos.state.mn.us/Business/Search"),
    ("MS", "Mississippi", "https://www.sos.ms.gov/business-services", "https://corp.sos.ms.gov/corp/portal/c/page/corpBusinessIdSearch/portal.aspx"),
    ("MO", "Missouri", "https://www.sos.mo.gov/business", "https://bsd.sos.mo.gov/BusinessEntity/BESearch.aspx?SearchType=0"),
    ("MT", "Montana", "https://sosmt.gov/business/", "https://biz.sosmt.gov/search/business"),
    ("NE", "Nebraska", "https://sos.nebraska.gov/business-services", "https://www.nebraska.gov/sos/corp/corpsearch.cgi"),
    ("NV", "Nevada", "https://www.nvsos.gov/sos/businesses", "https://esos.nv.gov/EntitySearch/OnlineEntitySearch"),
    ("NH", "New Hampshire", "https://www.sos.nh.gov/corporation-ucc-securities", "https://quickstart.sos.nh.gov/online/BusinessInquire"),
    ("NJ", "New Jersey", "https://www.nj.gov/treasury/revenue/", "https://www.njportal.com/DOR/BusinessNameSearch"),
    ("NM", "New Mexico", "https://www.sos.nm.gov/business-services/", "https://enterprise.sos.nm.gov/search/business"),
    ("NY", "New York", "https://dos.ny.gov/corporations-state-records-and-ucc", "https://apps.dos.ny.gov/publicInquiry/"),
    ("NC", "North Carolina", "https://www.sosnc.gov/divisions/business_registration", "https://www.sosnc.gov/online_services/search/by_title/_Business_Registration"),
    ("ND", "North Dakota", "https://www.sos.nd.gov/business/business-services", "https://firststop.sos.nd.gov/search/business"),
    ("OH", "Ohio", "https://www.ohiosos.gov/businesses/", "https://businesssearch.ohiosos.gov/"),
    ("OK", "Oklahoma", "https://www.sos.ok.gov/business/default.aspx", "https://www.sos.ok.gov/corp/corpInquiryFind.aspx"),
    ("OR", "Oregon", "https://sos.oregon.gov/business/Pages/default.aspx", "https://egov.sos.state.or.us/br/pkg_web_name_srch_inq.login"),
    ("PA", "Pennsylvania", "https://www.dos.pa.gov/BusinessCharities/Business/Pages/default.aspx", "https://file.dos.pa.gov/search/business"),
    ("RI", "Rhode Island", "https://www.sos.ri.gov/divisions/business-services", "https://business.sos.ri.gov/CorpWeb/CorpSearch/CorpSearch.aspx"),
    ("SC", "South Carolina", "https://sos.sc.gov/online-filings", "https://businessfilings.sc.gov/BusinessFiling/Entity/Search"),
    ("SD", "South Dakota", "https://sdsos.gov/business-services/default.aspx", "https://sosenterprise.sd.gov/BusinessServices/Business/FilingSearch.aspx"),
    ("TN", "Tennessee", "https://sos.tn.gov/businesses", "https://tnbear.tn.gov/Ecommerce/FilingSearch.aspx"),
    ("TX", "Texas", "https://www.sos.state.tx.us/corp/index.shtml", "https://www.sos.state.tx.us/corp/sosda/index.shtml"),
    ("UT", "Utah", "https://corporations.utah.gov/", "https://businessregistration.utah.gov/EntitySearch/OnlineEntitySearch"),
    ("VT", "Vermont", "https://sos.vermont.gov/corporations/", "https://bizfilings.vermont.gov/online/BusinessInquire/"),
    ("VA", "Virginia", "https://www.scc.virginia.gov/pages/Clerk-s-Office", "https://cis.scc.virginia.gov/EntitySearch/Index"),
    ("WA", "Washington", "https://www.sos.wa.gov/corporations-charities", "https://ccfs.sos.wa.gov/#/BusinessSearch"),
    ("WV", "West Virginia", "https://sos.wv.gov/business/Pages/default.aspx", "https://apps.sos.wv.gov/business/corporations/"),
    ("WI", "Wisconsin", "https://www.wdfi.org/corporations/", "https://www.wdfi.org/apps/CorpSearch/Search.aspx"),
    ("WY", "Wyoming", "https://sos.wyo.gov/Business/Default.aspx", "https://wyobiz.wyo.gov/Business/FilingSearch.aspx"),
)

US_STATES: dict[str, StateInfo] = {
    code: StateInfo(code=code, name=name, filing_office_url=office, name_search_url=search)
    for code, name, office, search in _DATA
}


def state_info(code: str) -> StateInfo:
    """The curated record for a USPS state code (case-insensitive); ``InvalidStateError`` otherwise."""
    key = (code or "").strip().upper()
    info = US_STATES.get(key)
    if info is None:
        raise InvalidStateError(
            f"I don't recognise the state \"{code}\". Use a US state code such as DE or WY.",
            details={"state": code},
        )
    return info
