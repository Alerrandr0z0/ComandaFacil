import os
import re

docs_dir = "/home/alerrandro/Desktop/ComandaFacil/docs/diagrama/Payment"

for f in sorted(os.listdir(docs_dir)):
    if f.endswith(".html") and not f.startswith("uml-") and not f.startswith("package-"):
        path = os.path.join(docs_dir, f)
        name = f.replace(".html", "")
        print("\n========================================")
        print(f"📦 Class/Interface: {name}")
        print("========================================")

        with open(path, encoding="utf-8") as file:
            content = file.read()

            # Look for Field Summary
            field_summary_match = re.search(
                r"<!-- =========== FIELD SUMMARY =========== -->.*?<TABLE.*?>(.*?)</TABLE>",
                content,
                re.DOTALL | re.IGNORECASE,
            )
            if field_summary_match:
                print("  🔹 Fields:")
                table_content = field_summary_match.group(1)
                for tr in re.findall(r"<TR.*?>.*?</TR>", table_content, re.DOTALL | re.IGNORECASE):
                    tds = re.findall(r"<TD.*?>(.*?)</TD>", tr, re.DOTALL | re.IGNORECASE)
                    if len(tds) >= 2:
                        ftype = re.sub(r"<.*?>|\s+", " ", tds[0]).strip()
                        fname = re.sub(r"<.*?>|\s+", " ", tds[1]).strip()
                        print(f"    - {fname}: {ftype}")

            # Look for Method Summary
            method_summary_match = re.search(
                r"<!-- ========== METHOD SUMMARY =========== -->.*?<TABLE.*?>(.*?)</TABLE>",
                content,
                re.DOTALL | re.IGNORECASE,
            )
            if method_summary_match:
                print("  🔸 Methods:")
                table_content = method_summary_match.group(1)
                for tr in re.findall(r"<TR.*?>.*?</TR>", table_content, re.DOTALL | re.IGNORECASE):
                    tds = re.findall(r"<TD.*?>(.*?)</TD>", tr, re.DOTALL | re.IGNORECASE)
                    if len(tds) >= 2:
                        mtype = re.sub(r"<.*?>|\s+", " ", tds[0]).strip()
                        mname = re.sub(r"<.*?>|\s+", " ", tds[1]).strip()
                        print(f"    - {mname} -> {mtype}")
