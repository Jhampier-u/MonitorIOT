import java.util.List;

import org.eclipse.emf.common.util.Diagnostic;
import org.eclipse.emf.common.util.URI;
import org.eclipse.emf.ecore.EObject;
import org.eclipse.emf.ecore.EPackage;
import org.eclipse.emf.ecore.resource.Resource;
import org.eclipse.emf.ecore.resource.ResourceSet;
import org.eclipse.emf.ecore.resource.impl.ResourceSetImpl;
import org.eclipse.emf.ecore.util.Diagnostician;
import org.eclipse.emf.ecore.xmi.impl.EcoreResourceFactoryImpl;
import org.eclipse.emf.ecore.xmi.impl.XMIResourceFactoryImpl;

/**
 * Comprueba con EMF (la misma librería que usa Obeo Designer) que un XMI se puede
 * abrir y cumple el metamodelo. Uso: java -cp <jars de EMF> EmfCheck.java metamodelo.ecore modelo...
 */
public class EmfCheck {
    public static void main(String[] args) {
        ResourceSet rs = new ResourceSetImpl();
        rs.getResourceFactoryRegistry().getExtensionToFactoryMap().put("ecore", new EcoreResourceFactoryImpl());
        rs.getResourceFactoryRegistry().getExtensionToFactoryMap().put("*", new XMIResourceFactoryImpl());
        Resource ecore = rs.getResource(URI.createFileURI(args[0]), true);
        EPackage pkg = (EPackage) ecore.getContents().get(0);
        rs.getPackageRegistry().put(pkg.getNsURI(), pkg);

        int failures = 0;
        for (int i = 1; i < args.length; i++) {
            String file = args[i];
            try {
                Resource r = rs.getResource(URI.createFileURI(file), true);
                List<Resource.Diagnostic> loadErrors = r.getErrors();
                EObject root = r.getContents().get(0);
                Diagnostic d = Diagnostician.INSTANCE.validate(root);
                boolean ok = loadErrors.isEmpty() && d.getSeverity() < Diagnostic.ERROR;
                System.out.println((ok ? "OK    " : "ERROR ") + file);
                for (Resource.Diagnostic e : loadErrors) System.out.println("   load: " + e.getMessage());
                for (Diagnostic c : d.getChildren()) System.out.println("   " + c.getMessage());
                if (!ok) failures++;
            } catch (RuntimeException e) {
                System.out.println("ERROR " + file + "\n   " + e.getMessage());
                failures++;
            }
        }
        System.exit(failures == 0 ? 0 : 1);
    }
}
