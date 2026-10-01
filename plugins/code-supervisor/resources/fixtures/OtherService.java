package demo;

public class OtherService {

    public String buildTitle(String givenName, String familyName, String town) {
        StringBuilder sb = new StringBuilder();
        sb.append(givenName.trim().toUpperCase());
        sb.append(" - ");
        sb.append(familyName.trim().toUpperCase());
        sb.append(" (");
        sb.append(town.trim());
        sb.append(")");
        return sb.toString();
    }
}
