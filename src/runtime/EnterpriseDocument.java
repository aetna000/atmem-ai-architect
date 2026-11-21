/* Credentialless, single-document Tika bridge. Configuration is operator-owned.
 * Run inside a network-isolated, resource-limited container; Tika is not a sandbox.
 * No URL, filename, parser option or environment setting comes from a document.
 */
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.Set;
import org.apache.tika.detect.DefaultDetector;
import org.apache.tika.io.TikaInputStream;
import org.apache.tika.metadata.Metadata;
import org.apache.tika.metadata.TikaCoreProperties;
import org.apache.tika.parser.AutoDetectParser;
import org.apache.tika.parser.ParseContext;
import org.apache.tika.parser.RecursiveParserWrapper;
import org.apache.tika.parser.microsoft.OfficeParserConfig;
import org.apache.tika.parser.ocr.TesseractOCRConfig;
import org.apache.tika.sax.BasicContentHandlerFactory;
import org.apache.tika.sax.RecursiveParserWrapperHandler;

public final class EnterpriseDocument {
    private static final int LIMIT = 200000;
    private static final Set<String> TYPES = Set.of(
        "text/plain", "text/html", "application/rtf",
        "application/msword", "application/vnd.ms-excel", "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.oasis.opendocument.text", "application/vnd.oasis.opendocument.spreadsheet",
        "application/vnd.oasis.opendocument.presentation");

    public static void main(String[] args) {
        try {
            if (args.length != 1) throw new IllegalArgumentException();
            Path input = Path.of(args[0]);
            if (!Files.isRegularFile(input) || Files.size(input) > 10000000 || Files.size(input) == 0)
                throw new IllegalArgumentException();
            Metadata root = new Metadata();
            String detected;
            try (TikaInputStream stream = TikaInputStream.get(input)) {
                detected = new DefaultDetector().detect(stream, root).toString();
            }
            if (!TYPES.contains(detected)) {
                System.out.print("rejected\nunsupported_format\n");
                System.exit(2);
            }
            AutoDetectParser parser = new AutoDetectParser();
            ParseContext context = new ParseContext();
            OfficeParserConfig office = new OfficeParserConfig();
            office.setExtractMacros(false);
            office.setIncludeDeletedContent(false);
            office.setIncludeMoveFromContent(false);
            office.setIncludeHeadersAndFooters(true);
            office.setIncludeSlideNotes(true);
            context.set(OfficeParserConfig.class, office);
            TesseractOCRConfig ocr = new TesseractOCRConfig();
            ocr.setLanguage("eng");
            ocr.setTimeoutSeconds(15);
            ocr.setEnableImagePreprocessing(false);
            context.set(TesseractOCRConfig.class, ocr);
            RecursiveParserWrapperHandler handler = new RecursiveParserWrapperHandler(
                new BasicContentHandlerFactory(BasicContentHandlerFactory.HANDLER_TYPE.TEXT, LIMIT), 64);
            // Recursive metadata exposes caught embedded/parse exceptions and write
            // limits, which plain CLI text output can otherwise quietly conceal.
            try (TikaInputStream stream = TikaInputStream.get(input)) {
                new RecursiveParserWrapper(parser).parse(stream, handler, root, context);
            }
            StringBuilder text = new StringBuilder();
            for (Metadata item : handler.getMetadataList()) {
                for (String name : item.names()) {
                    if (name.startsWith("X-TIKA:EXCEPTION") || name.startsWith("X-TIKA:WARN") ||
                        name.contains("write_limit_reached") || name.contains("embedded_resource_limit_reached"))
                        throw new IllegalArgumentException();
                }
                String content = item.get(TikaCoreProperties.TIKA_CONTENT);
                if (content != null && !content.isBlank()) text.append(content.strip()).append('\n');
                if (text.length() > LIMIT) throw new IllegalArgumentException();
            }
            byte[] result = text.toString().strip().getBytes(StandardCharsets.UTF_8);
            if (result.length == 0 || result.length > LIMIT) throw new IllegalArgumentException();
            System.out.print("ok\n" + detected + "\n" + Base64.getEncoder().encodeToString(result) + "\n");
        } catch (Throwable failure) {
            // Native parser messages can contain private text, filenames and URLs.
            System.out.print("rejected\nextraction_failed\n");
            System.exit(2);
        }
    }
}
