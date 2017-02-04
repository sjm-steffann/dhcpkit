%bcond_without systemd

%define name dhcpkit
%define version 1.0.5b1
%define unmangled_version 1.0.5b1
%define release 2%{?dist}

Summary: A DHCP library and server for IPv6 written in Python
Name: %{name}
Version: %{version}
Release: %{release}
Source0: https://pypi.debian.net/%{name}/%{name}-%{unmangled_version}.tar.gz
License: GPLv3
Group: System Environment/Daemons
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Sander Steffann <sander@dhcpkit.org>
Packager: Sander Steffann <sander@dhcpkit.org>
Requires: python34-netifaces python34-setuptools python34-ZConfig python34-cached-property
Url: https://github.com/sjm-steffann/dhcpkit

%if %{with systemd}
BuildRequires: systemd-units
%{?systemd_requires}
%endif


%description
DHCPKit
=======

This package contains a flexible DHCPv6 server written in Python 3.4+. Its purpose is to provide a framework for DHCP
services. It was written for ISPs to use in provisioning their customers according to their own business rules. It can
be integrated into existing ISP management and provisioning tools. Writing extensions to DHCPKit is very easy!

The `official documentation <http://dhcpkit.readthedocs.io>`_ is hosted by `Read the Docs <https://readthedocs.org>`_.


%prep
%setup -n %{name}-%{unmangled_version}


%build
python3 setup.py build


%install
python3 setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

mkdir -p $RPM_BUILD_ROOT/etc/dhcpkit
if [ -f examples/ipv6-dhcpd%{?dist}.conf ]; then
	cp examples/ipv6-dhcpd%{?dist}.conf $RPM_BUILD_ROOT/etc/dhcpkit/ipv6-dhcpd.conf
else
	cp examples/ipv6-dhcpd.conf $RPM_BUILD_ROOT/etc/dhcpkit/ipv6-dhcpd.conf
fi

mkdir -p $RPM_BUILD_ROOT/etc/init
if [ -f rpm/dhcpkit.ipv6-dhcpd%{?dist}.upstart ]; then
	cp rpm/dhcpkit.ipv6-dhcpd%{?dist}.upstart $RPM_BUILD_ROOT/etc/init/ipv6-dhcpd.conf
else
	cp rpm/dhcpkit.ipv6-dhcpd.upstart $RPM_BUILD_ROOT/etc/init/ipv6-dhcpd.conf
fi

mkdir -p $RPM_BUILD_ROOT/etc/init.d
if [ -f rpm/dhcpkit.ipv6-dhcpd%{?dist}.init ]; then
	cp rpm/dhcpkit.ipv6-dhcpd%{?dist}.init $RPM_BUILD_ROOT/etc/init.d/ipv6-dhcpd
else
	cp rpm/dhcpkit.ipv6-dhcpd.init $RPM_BUILD_ROOT/etc/init.d/ipv6-dhcpd
fi

%if %{with systemd}
	mkdir -p $RPM_BUILD_ROOT/%{_unitdir}
	if [ -f rpm/dhcpkit.ipv6-dhcpd%{?dist}.service ]; then
		cp rpm/dhcpkit.ipv6-dhcpd%{?dist}.service %{_unitdir}/ipv6-dhcpd.service
	else
		cp rpm/dhcpkit.ipv6-dhcpd.service %{_unitdir}/ipv6-dhcpd.service
	fi
%endif


%post
%if %{with systemd} && 0%{?systemd_post:1}
	%systemd_post ipv6-dhcpd.service
%else
	if [ $1 -eq 1 ]; then
		/sbin/chkconfig --add ipv6-dhcpd || true
	fi
%endif


%preun
%if %{with systemd} && 0%{?systemd_preun:1}
	%systemd_preun ipv6-dhcpd.service
%else
	if [ $1 -eq 0 ]; then
		/sbin/service ipv6-dhcpd stop &>/dev/null || true
		/sbin/chkconfig --del ipv6-dhcpd || true
	fi
%endif


%postun
%if %{with systemd} && 0%{?systemd_postun:1}
	%systemd_postun ipv6-dhcpd.service
%endif


%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
/etc/dhcpkit/ipv6-dhcpd.conf
/etc/init/ipv6-dhcpd.conf
/etc/init.d/ipv6-dhcpd      
